"""도구 관리자 - 모든 도구의 등록, 관리 및 실행을 담당"""

import asyncio
from typing import Dict, List, Optional, Any, Type, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from .base_tool import BaseTool, ToolResult, ToolType, ToolStatus, ToolConfig
from .web_scraper import WebScraperTool
from .api_client import APIClientTool
from .database_tool import DatabaseTool
from .file_processor import FileProcessorTool
from core.logger import log_function_call, get_logger
from core.config import get_config


class ToolManagerStatus(Enum):
    """도구 관리자 상태"""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class ToolRegistration:
    """도구 등록 정보"""
    tool: BaseTool
    registered_at: datetime
    last_used: Optional[datetime] = None
    usage_count: int = 0
    error_count: int = 0
    total_execution_time: float = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecution:
    """도구 실행 정보"""
    execution_id: str
    tool_name: str
    parameters: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: ToolStatus = ToolStatus.IDLE
    result: Optional[ToolResult] = None
    execution_time: float = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolManager:
    """도구 관리자"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """도구 관리자 초기화"""
        self.config = config or {}
        self.status = ToolManagerStatus.INITIALIZING
        self.logger = get_logger(__name__)
        
        # 등록된 도구들
        self.tools: Dict[str, ToolRegistration] = {}
        
        # 실행 중인 작업들
        self.active_executions: Dict[str, ToolExecution] = {}
        
        # 실행 기록
        self.execution_history: List[ToolExecution] = []
        
        # 설정
        self.max_concurrent_executions = self.config.get("max_concurrent_executions", 10)
        self.execution_timeout = self.config.get("execution_timeout", 300)  # 5분
        self.history_retention_days = self.config.get("history_retention_days", 7)
        self.auto_cleanup_enabled = self.config.get("auto_cleanup_enabled", True)
        
        # 통계
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.total_execution_time = 0
        
        # 이벤트 핸들러
        self.event_handlers = {
            "tool_registered": [],
            "tool_unregistered": [],
            "execution_started": [],
            "execution_completed": [],
            "execution_failed": [],
            "execution_timeout": []
        }
        
        # 자동 정리 작업
        self._cleanup_task = None
        
        # 기본 도구들 등록
        self._register_default_tools()
        
        self.status = ToolManagerStatus.READY
    
    def _register_default_tools(self):
        """기본 도구들 등록"""
        default_tools = [
            WebScraperTool(),
            APIClientTool(),
            DatabaseTool(),
            FileProcessorTool()
        ]
        
        for tool in default_tools:
            self.register_tool(tool)
    
    @log_function_call
    def register_tool(self, tool: BaseTool, metadata: Dict[str, Any] = None) -> bool:
        """도구 등록"""
        try:
            if tool.name in self.tools:
                raise ValueError(f"도구 '{tool.name}'이 이미 등록되어 있습니다")
            
            # 도구 등록
            registration = ToolRegistration(
                tool=tool,
                registered_at=datetime.now(),
                metadata=metadata or {}
            )
            
            self.tools[tool.name] = registration
            
            # 이벤트 발생
            self._emit_event("tool_registered", {
                "tool_name": tool.name,
                "tool_type": tool.tool_type.value,
                "registered_at": registration.registered_at.isoformat()
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"도구 등록 실패: {str(e)}")
            return False
    
    @log_function_call
    def unregister_tool(self, tool_name: str) -> bool:
        """도구 등록 해제"""
        try:
            if tool_name not in self.tools:
                raise ValueError(f"도구 '{tool_name}'을 찾을 수 없습니다")
            
            # 실행 중인 작업 확인
            active_executions = [exec_id for exec_id, execution in self.active_executions.items() 
                               if execution.tool_name == tool_name]
            
            if active_executions:
                raise ValueError(f"도구 '{tool_name}'이 실행 중입니다. 먼저 실행을 중단하세요")
            
            # 도구 등록 해제
            registration = self.tools.pop(tool_name)
            
            # 이벤트 발생
            self._emit_event("tool_unregistered", {
                "tool_name": tool_name,
                "unregistered_at": datetime.now().isoformat(),
                "usage_count": registration.usage_count
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"도구 등록 해제 실패: {str(e)}")
            return False
    
    @log_function_call
    async def execute_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any] = None,
        execution_id: str = None,
        timeout: Optional[float] = None
    ) -> ToolResult:
        """도구 실행"""
        if self.status != ToolManagerStatus.READY:
            return ToolResult.error_result(f"도구 관리자가 준비되지 않았습니다: {self.status.value}")
        
        # 동시 실행 제한 확인
        if len(self.active_executions) >= self.max_concurrent_executions:
            return ToolResult.error_result("최대 동시 실행 수를 초과했습니다")
        
        # 도구 존재 확인
        if tool_name not in self.tools:
            return ToolResult.error_result(f"도구 '{tool_name}'을 찾을 수 없습니다")
        
        registration = self.tools[tool_name]
        
        # 도구 활성화 확인
        if not registration.enabled:
            return ToolResult.error_result(f"도구 '{tool_name}'이 비활성화되어 있습니다")
        
        # 실행 ID 생성
        if not execution_id:
            execution_id = f"{tool_name}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # 실행 정보 생성
        execution = ToolExecution(
            execution_id=execution_id,
            tool_name=tool_name,
            parameters=parameters or {},
            started_at=datetime.now()
        )
        
        self.active_executions[execution_id] = execution
        
        try:
            self.status = ToolManagerStatus.BUSY
            
            # 이벤트 발생
            self._emit_event("execution_started", {
                "execution_id": execution_id,
                "tool_name": tool_name,
                "started_at": execution.started_at.isoformat()
            })
            
            # 도구 실행 (타임아웃 적용)
            execution_timeout = timeout or self.execution_timeout
            
            try:
                result = await asyncio.wait_for(
                    registration.tool.execute(**execution.parameters),
                    timeout=execution_timeout
                )
                
                execution.status = ToolStatus.COMPLETED
                execution.result = result
                
                # 통계 업데이트
                if result.success:
                    self.successful_executions += 1
                else:
                    self.failed_executions += 1
                    registration.error_count += 1
                
            except asyncio.TimeoutError:
                execution.status = ToolStatus.TIMEOUT
                execution.error_message = f"실행 시간 초과 ({execution_timeout}초)"
                result = ToolResult.error_result(execution.error_message)
                
                self.failed_executions += 1
                registration.error_count += 1
                
                # 이벤트 발생
                self._emit_event("execution_timeout", {
                    "execution_id": execution_id,
                    "tool_name": tool_name,
                    "timeout": execution_timeout
                })
            
            # 실행 완료 처리
            execution.completed_at = datetime.now()
            execution.execution_time = (execution.completed_at - execution.started_at).total_seconds()
            
            # 통계 업데이트
            self.total_executions += 1
            self.total_execution_time += execution.execution_time
            registration.usage_count += 1
            registration.last_used = execution.completed_at
            registration.total_execution_time += execution.execution_time
            
            # 활성 실행에서 제거
            self.active_executions.pop(execution_id, None)
            
            # 실행 기록에 추가
            self.execution_history.append(execution)
            
            # 이벤트 발생
            if result.success:
                self._emit_event("execution_completed", {
                    "execution_id": execution_id,
                    "tool_name": tool_name,
                    "execution_time": execution.execution_time,
                    "completed_at": execution.completed_at.isoformat()
                })
            else:
                self._emit_event("execution_failed", {
                    "execution_id": execution_id,
                    "tool_name": tool_name,
                    "error_message": result.error_message,
                    "completed_at": execution.completed_at.isoformat()
                })
            
            return result
            
        except Exception as e:
            # 오류 처리
            execution.status = ToolStatus.ERROR
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            execution.execution_time = (execution.completed_at - execution.started_at).total_seconds()
            
            # 통계 업데이트
            self.failed_executions += 1
            registration.error_count += 1
            
            # 활성 실행에서 제거
            self.active_executions.pop(execution_id, None)
            
            # 실행 기록에 추가
            self.execution_history.append(execution)
            
            # 이벤트 발생
            self._emit_event("execution_failed", {
                "execution_id": execution_id,
                "tool_name": tool_name,
                "error_message": str(e),
                "completed_at": execution.completed_at.isoformat()
            })
            
            return ToolResult.error_result(f"도구 실행 실패: {str(e)}")
            
        finally:
            self.status = ToolManagerStatus.READY
    
    @log_function_call
    async def execute_tools_batch(
        self, 
        tool_requests: List[Dict[str, Any]],
        max_concurrent: Optional[int] = None
    ) -> List[ToolResult]:
        """여러 도구 배치 실행"""
        max_concurrent = max_concurrent or min(len(tool_requests), self.max_concurrent_executions)
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_single(request: Dict[str, Any]) -> ToolResult:
            async with semaphore:
                return await self.execute_tool(
                    tool_name=request.get("tool_name"),
                    parameters=request.get("parameters", {}),
                    execution_id=request.get("execution_id"),
                    timeout=request.get("timeout")
                )
        
        # 모든 도구 실행
        tasks = [execute_single(request) for request in tool_requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외를 ToolResult로 변환
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(ToolResult.error_result(f"배치 실행 실패: {str(result)}"))
            else:
                processed_results.append(result)
        
        return processed_results
    
    @log_function_call
    def cancel_execution(self, execution_id: str) -> bool:
        """실행 중인 작업 취소"""
        try:
            if execution_id not in self.active_executions:
                return False
            
            execution = self.active_executions[execution_id]
            tool_registration = self.tools.get(execution.tool_name)
            
            if tool_registration:
                # 도구의 취소 메서드 호출
                tool_registration.tool.cancel()
            
            # 실행 상태 업데이트
            execution.status = ToolStatus.CANCELLED
            execution.completed_at = datetime.now()
            execution.execution_time = (execution.completed_at - execution.started_at).total_seconds()
            execution.error_message = "사용자에 의해 취소됨"
            
            # 활성 실행에서 제거
            self.active_executions.pop(execution_id, None)
            
            # 실행 기록에 추가
            self.execution_history.append(execution)
            
            return True
            
        except Exception as e:
            self.logger.error(f"실행 취소 실패: {str(e)}")
            return False
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """도구 정보 조회"""
        if tool_name not in self.tools:
            return None
        
        registration = self.tools[tool_name]
        tool = registration.tool
        
        return {
            "name": tool.name,
            "type": tool.tool_type.value,
            "description": tool.get_description(),
            "parameters_schema": tool.get_parameters_schema(),
            "status": tool.status.value,
            "enabled": registration.enabled,
            "registered_at": registration.registered_at.isoformat(),
            "last_used": registration.last_used.isoformat() if registration.last_used else None,
            "usage_count": registration.usage_count,
            "error_count": registration.error_count,
            "total_execution_time": registration.total_execution_time,
            "average_execution_time": registration.total_execution_time / registration.usage_count if registration.usage_count > 0 else 0,
            "error_rate": registration.error_count / registration.usage_count if registration.usage_count > 0 else 0,
            "metadata": registration.metadata
        }
    
    def list_tools(self, tool_type: Optional[ToolType] = None, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """등록된 도구 목록 조회"""
        tools_info = []
        
        for tool_name, registration in self.tools.items():
            # 필터링
            if tool_type and registration.tool.tool_type != tool_type:
                continue
            if enabled_only and not registration.enabled:
                continue
            
            tool_info = self.get_tool_info(tool_name)
            if tool_info:
                tools_info.append(tool_info)
        
        return tools_info
    
    def get_execution_info(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """실행 정보 조회"""
        # 활성 실행 확인
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]
            return {
                "execution_id": execution.execution_id,
                "tool_name": execution.tool_name,
                "parameters": execution.parameters,
                "status": execution.status.value,
                "started_at": execution.started_at.isoformat(),
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "execution_time": execution.execution_time,
                "error_message": execution.error_message,
                "is_active": True,
                "metadata": execution.metadata
            }
        
        # 실행 기록 확인
        for execution in self.execution_history:
            if execution.execution_id == execution_id:
                return {
                    "execution_id": execution.execution_id,
                    "tool_name": execution.tool_name,
                    "parameters": execution.parameters,
                    "status": execution.status.value,
                    "started_at": execution.started_at.isoformat(),
                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    "execution_time": execution.execution_time,
                    "result": execution.result.to_dict() if execution.result else None,
                    "error_message": execution.error_message,
                    "is_active": False,
                    "metadata": execution.metadata
                }
        
        return None
    
    def list_executions(
        self, 
        tool_name: Optional[str] = None,
        status: Optional[ToolStatus] = None,
        limit: Optional[int] = None,
        include_active: bool = True
    ) -> List[Dict[str, Any]]:
        """실행 목록 조회"""
        executions = []
        
        # 활성 실행 추가
        if include_active:
            for execution in self.active_executions.values():
                if tool_name and execution.tool_name != tool_name:
                    continue
                if status and execution.status != status:
                    continue
                
                executions.append({
                    "execution_id": execution.execution_id,
                    "tool_name": execution.tool_name,
                    "status": execution.status.value,
                    "started_at": execution.started_at.isoformat(),
                    "execution_time": execution.execution_time,
                    "is_active": True
                })
        
        # 실행 기록 추가
        for execution in reversed(self.execution_history):
            if tool_name and execution.tool_name != tool_name:
                continue
            if status and execution.status != status:
                continue
            
            executions.append({
                "execution_id": execution.execution_id,
                "tool_name": execution.tool_name,
                "status": execution.status.value,
                "started_at": execution.started_at.isoformat(),
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "execution_time": execution.execution_time,
                "success": execution.result.success if execution.result else False,
                "is_active": False
            })
            
            if limit and len(executions) >= limit:
                break
        
        return executions[:limit] if limit else executions
    
    def enable_tool(self, tool_name: str) -> bool:
        """도구 활성화"""
        if tool_name not in self.tools:
            return False
        
        self.tools[tool_name].enabled = True
        return True
    
    def disable_tool(self, tool_name: str) -> bool:
        """도구 비활성화"""
        if tool_name not in self.tools:
            return False
        
        self.tools[tool_name].enabled = False
        return True
    
    def add_event_handler(self, event_type: str, handler):
        """이벤트 핸들러 추가"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
    
    def remove_event_handler(self, event_type: str, handler):
        """이벤트 핸들러 제거"""
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """이벤트 발생"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    handler(event_type, data)
                except Exception as e:
                    self.logger.error(f"이벤트 핸들러 실행 실패: {str(e)}")
    
    @log_function_call
    def start_auto_cleanup(self):
        """자동 정리 작업 시작"""
        if self.auto_cleanup_enabled and not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._auto_cleanup_loop())
    
    def stop_auto_cleanup(self):
        """자동 정리 작업 중지"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
    
    async def _auto_cleanup_loop(self):
        """자동 정리 루프"""
        while True:
            try:
                await asyncio.sleep(3600)  # 1시간마다 실행
                await self.cleanup_old_executions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"자동 정리 작업 실패: {str(e)}")
    
    @log_function_call
    async def cleanup_old_executions(self):
        """오래된 실행 기록 정리"""
        cutoff_date = datetime.now() - timedelta(days=self.history_retention_days)
        
        # 오래된 실행 기록 제거
        original_count = len(self.execution_history)
        self.execution_history = [
            execution for execution in self.execution_history
            if execution.started_at > cutoff_date
        ]
        
        cleaned_count = original_count - len(self.execution_history)
        if cleaned_count > 0:
            self.logger.info(f"{cleaned_count}개의 오래된 실행 기록을 정리했습니다")
    
    def get_statistics(self) -> Dict[str, Any]:
        """도구 관리자 통계 조회"""
        return {
            "status": self.status.value,
            "registered_tools": len(self.tools),
            "enabled_tools": len([t for t in self.tools.values() if t.enabled]),
            "active_executions": len(self.active_executions),
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": self.successful_executions / self.total_executions if self.total_executions > 0 else 0,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": self.total_execution_time / self.total_executions if self.total_executions > 0 else 0,
            "execution_history_size": len(self.execution_history),
            "max_concurrent_executions": self.max_concurrent_executions,
            "execution_timeout": self.execution_timeout,
            "auto_cleanup_enabled": self.auto_cleanup_enabled,
            "history_retention_days": self.history_retention_days
        }
    
    def export_statistics(self, format: str = "json") -> str:
        """통계 내보내기"""
        stats = self.get_statistics()
        
        # 도구별 통계 추가
        tool_stats = {}
        for tool_name, registration in self.tools.items():
            tool_stats[tool_name] = {
                "usage_count": registration.usage_count,
                "error_count": registration.error_count,
                "total_execution_time": registration.total_execution_time,
                "average_execution_time": registration.total_execution_time / registration.usage_count if registration.usage_count > 0 else 0,
                "error_rate": registration.error_count / registration.usage_count if registration.usage_count > 0 else 0,
                "last_used": registration.last_used.isoformat() if registration.last_used else None
            }
        
        stats["tool_statistics"] = tool_stats
        
        if format.lower() == "json":
            return json.dumps(stats, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"지원하지 않는 형식: {format}")
    
    @log_function_call
    async def shutdown(self):
        """도구 관리자 종료"""
        self.status = ToolManagerStatus.SHUTDOWN
        
        # 자동 정리 작업 중지
        self.stop_auto_cleanup()
        
        # 활성 실행 취소
        active_execution_ids = list(self.active_executions.keys())
        for execution_id in active_execution_ids:
            self.cancel_execution(execution_id)
        
        # 모든 도구 정리
        for registration in self.tools.values():
            try:
                registration.tool.cleanup()
            except Exception as e:
                self.logger.error(f"도구 정리 실패: {str(e)}")
        
        self.logger.info("도구 관리자가 종료되었습니다")


# 전역 도구 관리자 인스턴스
_tool_manager_instance = None


def get_tool_manager() -> ToolManager:
    """전역 도구 관리자 인스턴스 반환"""
    global _tool_manager_instance
    if _tool_manager_instance is None:
        _tool_manager_instance = ToolManager()
    return _tool_manager_instance


async def execute_tool(tool_name: str, **parameters) -> ToolResult:
    """도구 실행 편의 함수"""
    tool_manager = get_tool_manager()
    return await tool_manager.execute_tool(tool_name, parameters)