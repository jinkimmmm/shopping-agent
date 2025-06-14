"""기본 도구 클래스 - 모든 도구의 기본 인터페이스"""

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict

from core.logger import LoggerMixin, log_function_call
from core.config import get_config


class ToolType(Enum):
    """도구 유형"""
    WEB_SCRAPER = "web_scraper"
    FILE_MANAGER = "file_manager"
    DATA_PROCESSOR = "data_processor"
    API_CLIENT = "api_client"
    CALCULATOR = "calculator"
    EMAIL_SENDER = "email_sender"
    DATABASE = "database"
    CODE_EXECUTOR = "code_executor"
    CUSTOM = "custom"


class ToolStatus(Enum):
    """도구 상태"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ToolResult:
    """도구 실행 결과"""
    success: bool
    data: Any = None
    error_message: str = ""
    execution_time: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)
    
    @classmethod
    def success_result(cls, data: Any = None, execution_time: float = 0.0, metadata: Dict[str, Any] = None) -> 'ToolResult':
        """성공 결과 생성"""
        return cls(
            success=True,
            data=data,
            execution_time=execution_time,
            metadata=metadata or {}
        )
    
    @classmethod
    def error_result(cls, error_message: str, execution_time: float = 0.0, metadata: Dict[str, Any] = None) -> 'ToolResult':
        """실패 결과 생성"""
        return cls(
            success=False,
            error_message=error_message,
            execution_time=execution_time,
            metadata=metadata or {}
        )


@dataclass
class ToolConfig:
    """도구 설정"""
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_per_minute: int = 60
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    log_enabled: bool = True
    custom_settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_settings is None:
            self.custom_settings = {}


class BaseTool(ABC, LoggerMixin):
    """기본 도구 클래스"""
    
    def __init__(self, tool_name: str, tool_type: ToolType, config: ToolConfig = None):
        """도구 초기화"""
        super().__init__()
        
        self.tool_name = tool_name
        self.tool_type = tool_type
        self.config = config or ToolConfig()
        self.settings = get_config()
        
        # 상태 관리
        self.status = ToolStatus.IDLE
        self.created_at = datetime.now()
        self.last_used = None
        
        # 실행 통계
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_execution_time = 0.0
        
        # 캐시
        self.cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # 속도 제한
        self.rate_limit_timestamps: List[datetime] = []
        
        # 현재 실행 중인 작업
        self.current_task: Optional[asyncio.Task] = None
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """도구 실행 (하위 클래스에서 구현)"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """도구 설명 반환"""
        pass
    
    @abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        """매개변수 스키마 반환"""
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """매개변수 유효성 검사"""
        errors = []
        schema = self.get_parameters_schema()
        
        # 필수 매개변수 확인
        required = schema.get("required", [])
        for param in required:
            if param not in parameters:
                errors.append(f"필수 매개변수 누락: {param}")
        
        # 매개변수 타입 확인
        properties = schema.get("properties", {})
        for param, value in parameters.items():
            if param in properties:
                expected_type = properties[param].get("type")
                if expected_type and not self._check_type(value, expected_type):
                    errors.append(f"매개변수 {param}의 타입이 올바르지 않음: 예상 {expected_type}, 실제 {type(value).__name__}")
        
        return errors
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """타입 확인"""
        type_mapping = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)
        
        return True
    
    def _generate_cache_key(self, **kwargs) -> str:
        """캐시 키 생성"""
        # 매개변수를 정렬하여 일관된 키 생성
        sorted_params = sorted(kwargs.items())
        key_data = f"{self.tool_name}:{json.dumps(sorted_params, sort_keys=True)}"
        return key_data
    
    def _get_from_cache(self, cache_key: str) -> Optional[ToolResult]:
        """캐시에서 결과 조회"""
        if not self.config.cache_enabled:
            return None
        
        if cache_key not in self.cache:
            return None
        
        # TTL 확인
        timestamp = self.cache_timestamps.get(cache_key)
        if timestamp:
            age = datetime.now() - timestamp
            if age.total_seconds() > self.config.cache_ttl_seconds:
                # 만료된 캐시 제거
                del self.cache[cache_key]
                del self.cache_timestamps[cache_key]
                return None
        
        return self.cache[cache_key]
    
    def _save_to_cache(self, cache_key: str, result: ToolResult) -> None:
        """결과를 캐시에 저장"""
        if not self.config.cache_enabled or not result.success:
            return
        
        self.cache[cache_key] = result
        self.cache_timestamps[cache_key] = datetime.now()
    
    def _check_rate_limit(self) -> bool:
        """속도 제한 확인"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        
        # 1분 이내의 요청만 유지
        self.rate_limit_timestamps = [
            ts for ts in self.rate_limit_timestamps if ts > cutoff
        ]
        
        # 제한 확인
        if len(self.rate_limit_timestamps) >= self.config.rate_limit_per_minute:
            return False
        
        # 현재 요청 기록
        self.rate_limit_timestamps.append(now)
        return True
    
    @log_function_call
    async def run(self, **kwargs) -> ToolResult:
        """도구 실행 (공통 로직 포함)"""
        start_time = datetime.now()
        
        try:
            # 상태 업데이트
            self.status = ToolStatus.RUNNING
            self.last_used = start_time
            
            # 매개변수 유효성 검사
            validation_errors = self.validate_parameters(kwargs)
            if validation_errors:
                raise ValueError(f"매개변수 유효성 검사 실패: {', '.join(validation_errors)}")
            
            # 속도 제한 확인
            if not self._check_rate_limit():
                raise Exception(f"속도 제한 초과: 분당 최대 {self.config.rate_limit_per_minute}회")
            
            # 캐시 확인
            cache_key = self._generate_cache_key(**kwargs)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                self.logger.info(f"캐시에서 결과 반환: {cache_key}")
                self.status = ToolStatus.COMPLETED
                return cached_result
            
            # 실제 실행
            self.current_task = asyncio.create_task(self._execute_with_timeout(**kwargs))
            result = await self.current_task
            
            # 결과 처리
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            
            # 통계 업데이트
            self.execution_count += 1
            self.total_execution_time += execution_time
            
            if result.success:
                self.success_count += 1
                self.status = ToolStatus.COMPLETED
                # 캐시 저장
                self._save_to_cache(cache_key, result)
            else:
                self.failure_count += 1
                self.status = ToolStatus.FAILED
            
            return result
            
        except asyncio.TimeoutError:
            self.status = ToolStatus.TIMEOUT
            self.failure_count += 1
            execution_time = (datetime.now() - start_time).total_seconds()
            return ToolResult.error_result(
                f"도구 실행 타임아웃: {self.config.timeout_seconds}초",
                execution_time
            )
            
        except asyncio.CancelledError:
            self.status = ToolStatus.CANCELLED
            execution_time = (datetime.now() - start_time).total_seconds()
            return ToolResult.error_result(
                "도구 실행이 취소됨",
                execution_time
            )
            
        except Exception as e:
            self.status = ToolStatus.FAILED
            self.failure_count += 1
            execution_time = (datetime.now() - start_time).total_seconds()
            
            error_message = str(e)
            self.logger.error(f"도구 실행 실패: {error_message}")
            
            return ToolResult.error_result(error_message, execution_time)
        
        finally:
            self.current_task = None
    
    async def _execute_with_timeout(self, **kwargs) -> ToolResult:
        """타임아웃과 함께 실행"""
        return await asyncio.wait_for(
            self.execute(**kwargs),
            timeout=self.config.timeout_seconds
        )
    
    async def run_with_retry(self, **kwargs) -> ToolResult:
        """재시도와 함께 실행"""
        last_result = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                result = await self.run(**kwargs)
                
                if result.success:
                    return result
                
                last_result = result
                
                # 마지막 시도가 아니면 재시도 지연
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (2 ** attempt)  # 지수 백오프
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                last_result = ToolResult.error_result(str(e))
                
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
        
        return last_result or ToolResult.error_result("모든 재시도 실패")
    
    async def cancel(self) -> bool:
        """실행 중인 작업 취소"""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            try:
                await self.current_task
            except asyncio.CancelledError:
                pass
            
            self.status = ToolStatus.CANCELLED
            return True
        
        return False
    
    def clear_cache(self) -> None:
        """캐시 정리"""
        self.cache.clear()
        self.cache_timestamps.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """실행 통계 조회"""
        success_rate = self.success_count / self.execution_count if self.execution_count > 0 else 0.0
        avg_execution_time = self.total_execution_time / self.execution_count if self.execution_count > 0 else 0.0
        
        return {
            "tool_name": self.tool_name,
            "tool_type": self.tool_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": success_rate,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": avg_execution_time,
            "cache_size": len(self.cache),
            "rate_limit_remaining": max(0, self.config.rate_limit_per_minute - len(self.rate_limit_timestamps))
        }
    
    def get_info(self) -> Dict[str, Any]:
        """도구 정보 조회"""
        return {
            "name": self.tool_name,
            "type": self.tool_type.value,
            "description": self.get_description(),
            "parameters_schema": self.get_parameters_schema(),
            "config": asdict(self.config),
            "statistics": self.get_statistics()
        }
    
    def __str__(self) -> str:
        return f"{self.tool_name} ({self.tool_type.value})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.tool_name}>"