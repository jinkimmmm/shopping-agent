"""베이스 에이전트 클래스"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from core.logger import LoggerMixin, log_function_call
from ai.gemini_client import GeminiClient
from ai.agent_nlp_handler import ParsedIntent, AgentTask


class AgentType(Enum):
    """에이전트 유형"""
    MANAGER = "manager"
    WORKER = "worker"
    TESTER = "tester"
    SPECIALIST = "specialist"


class AgentStatus(Enum):
    """에이전트 상태"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class TaskStatus(Enum):
    """작업 상태"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentCapability:
    """에이전트 능력"""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class TaskExecution:
    """작업 실행 정보"""
    task_id: str
    agent_id: str
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: float = 0.0


@dataclass
class AgentMessage:
    """에이전트 메시지"""
    id: str
    sender_id: str
    receiver_id: str
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime
    priority: int = 1


class BaseAgent(ABC, LoggerMixin):
    """베이스 에이전트 클래스"""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        name: str,
        gemini_client: GeminiClient,
        capabilities: Optional[List[AgentCapability]] = None
    ):
        """에이전트 초기화"""
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.name = name
        self.gemini_client = gemini_client
        self.capabilities = capabilities or []
        
        # 상태 관리
        self.status = AgentStatus.IDLE
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        
        # 작업 관리
        self.current_tasks: Dict[str, TaskExecution] = {}
        self.completed_tasks: List[TaskExecution] = []
        self.task_queue: List[AgentTask] = []
        
        # 메시지 관리
        self.message_queue: List[AgentMessage] = []
        self.message_handlers: Dict[str, Callable] = {}
        
        # 성능 메트릭
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_execution_time": 0.0,
            "success_rate": 0.0
        }
        
        # 이벤트 루프
        self._running = False
        self._loop_task = None
        
        # 추가 속성들
        self.tools: List[str] = []
        self.active_executions: Dict[str, Any] = {}
        
        self.logger.info(
            f"에이전트 초기화 완료: {self.name} ({self.agent_type.value})",
            extra={"agent_id": self.agent_id}
        )
    
    @abstractmethod
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """작업 처리 (추상 메서드)"""
        pass
    
    @abstractmethod
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """메시지 처리 (추상 메서드)"""
        pass
    
    @log_function_call
    async def start(self):
        """에이전트 시작"""
        if self._running:
            self.logger.warning("에이전트가 이미 실행 중입니다")
            return
        
        self._running = True
        self.status = AgentStatus.IDLE
        self._loop_task = asyncio.create_task(self._main_loop())
        
        self.logger.info(f"에이전트 시작: {self.name}")
    
    @log_function_call
    async def stop(self):
        """에이전트 중지"""
        self._running = False
        self.status = AgentStatus.OFFLINE
        
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info(f"에이전트 중지: {self.name}")
    
    async def _main_loop(self):
        """메인 이벤트 루프"""
        while self._running:
            try:
                # 메시지 처리
                await self._process_messages()
                
                # 작업 처리
                await self._process_tasks()
                
                # 상태 업데이트
                await self._update_status()
                
                # 짧은 대기
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"메인 루프 오류: {e}")
                self.status = AgentStatus.ERROR
                await asyncio.sleep(1.0)
    
    async def _process_messages(self):
        """메시지 처리"""
        while self.message_queue:
            message = self.message_queue.pop(0)
            try:
                response = await self.handle_message(message)
                if response:
                    # 응답 메시지 전송 (실제 구현에서는 메시지 브로커 사용)
                    self.logger.info(f"응답 메시지 생성: {response.id}")
            except Exception as e:
                self.logger.error(f"메시지 처리 실패: {e}")
    
    async def _process_tasks(self):
        """작업 처리"""
        if self.status != AgentStatus.IDLE or not self.task_queue:
            return
        
        # 다음 작업 가져오기
        task = self.task_queue.pop(0)
        
        # 작업 실행 시작
        execution = TaskExecution(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status=TaskStatus.IN_PROGRESS,
            start_time=datetime.now()
        )
        
        self.current_tasks[task.task_id] = execution
        self.status = AgentStatus.BUSY
        
        try:
            # 작업 처리
            result = await self.process_task(task)
            
            # 성공 처리
            execution.status = TaskStatus.COMPLETED
            execution.end_time = datetime.now()
            execution.result = result
            execution.progress = 1.0
            
            self.metrics["tasks_completed"] += 1
            
            self.logger.info(
                f"작업 완료: {task.task_id}",
                extra={"agent_id": self.agent_id, "task_type": task.task_type.value}
            )
            
        except Exception as e:
            # 실패 처리
            execution.status = TaskStatus.FAILED
            execution.end_time = datetime.now()
            execution.error = str(e)
            
            self.metrics["tasks_failed"] += 1
            
            self.logger.error(
                f"작업 실패: {task.task_id} - {e}",
                extra={"agent_id": self.agent_id}
            )
        
        finally:
            # 정리
            self.completed_tasks.append(execution)
            del self.current_tasks[task.task_id]
            self.status = AgentStatus.IDLE
            self.last_activity = datetime.now()
            
            # 메트릭 업데이트
            self._update_metrics()
    
    async def _update_status(self):
        """상태 업데이트"""
        # 현재 작업 진행률 업데이트
        for execution in self.current_tasks.values():
            if execution.status == TaskStatus.IN_PROGRESS:
                # 시간 기반 진행률 추정 (실제로는 작업별로 구현)
                elapsed = (datetime.now() - execution.start_time).total_seconds()
                estimated_duration = 60.0  # 60초 추정
                execution.progress = min(elapsed / estimated_duration, 0.9)
    
    def _update_metrics(self):
        """메트릭 업데이트"""
        total_tasks = self.metrics["tasks_completed"] + self.metrics["tasks_failed"]
        
        if total_tasks > 0:
            self.metrics["success_rate"] = self.metrics["tasks_completed"] / total_tasks
        
        # 평균 실행 시간 계산
        if self.completed_tasks:
            total_time = sum(
                (task.end_time - task.start_time).total_seconds()
                for task in self.completed_tasks
                if task.end_time and task.status == TaskStatus.COMPLETED
            )
            completed_count = len([
                task for task in self.completed_tasks
                if task.status == TaskStatus.COMPLETED
            ])
            
            if completed_count > 0:
                self.metrics["average_execution_time"] = total_time / completed_count
    
    @log_function_call
    async def add_task(self, task: AgentTask) -> bool:
        """작업 추가"""
        try:
            # 의존성 확인
            if task.dependencies:
                for dep_id in task.dependencies:
                    if not self._is_dependency_satisfied(dep_id):
                        self.logger.warning(f"의존성 미충족: {dep_id}")
                        return False
            
            # 우선순위에 따라 삽입
            inserted = False
            for i, existing_task in enumerate(self.task_queue):
                if task.priority > existing_task.priority:
                    self.task_queue.insert(i, task)
                    inserted = True
                    break
            
            if not inserted:
                self.task_queue.append(task)
            
            self.logger.info(
                f"작업 추가: {task.task_id}",
                extra={"agent_id": self.agent_id, "queue_size": len(self.task_queue)}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"작업 추가 실패: {e}")
            return False
    
    def _is_dependency_satisfied(self, dependency_id: str) -> bool:
        """의존성 충족 확인"""
        return any(
            task.task_id == dependency_id and task.status == TaskStatus.COMPLETED
            for task in self.completed_tasks
        )
    
    @log_function_call
    async def send_message(self, message: AgentMessage):
        """메시지 전송"""
        # 실제 구현에서는 메시지 브로커나 이벤트 시스템 사용
        self.logger.info(
            f"메시지 전송: {message.id} -> {message.receiver_id}",
            extra={"message_type": message.message_type}
        )
    
    @log_function_call
    async def receive_message(self, message: AgentMessage):
        """메시지 수신"""
        self.message_queue.append(message)
        self.logger.info(
            f"메시지 수신: {message.id} from {message.sender_id}",
            extra={"message_type": message.message_type}
        )
    
    def add_capability(self, capability: AgentCapability):
        """능력 추가"""
        self.capabilities.append(capability)
        self.logger.info(f"능력 추가: {capability.name}")
    
    def has_capability(self, capability_name: str) -> bool:
        """능력 보유 확인"""
        return any(
            cap.name == capability_name and cap.enabled
            for cap in self.capabilities
        )
    
    async def create_workflow(self, workflow_data: Dict[str, Any]) -> str:
        """워크플로우 생성"""
        workflow_id = str(uuid.uuid4())
        self.logger.info(f"워크플로우 생성: {workflow_id}")
        return workflow_id
    
    async def start_workflow(self, workflow_id: str) -> bool:
        """워크플로우 시작"""
        self.logger.info(f"워크플로우 시작: {workflow_id}")
        return True
    
    def get_status_info(self) -> Dict[str, Any]:
        """상태 정보 조회"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "type": self.agent_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "current_tasks": len(self.current_tasks),
            "queued_tasks": len(self.task_queue),
            "completed_tasks": len(self.completed_tasks),
            "capabilities": [cap.name for cap in self.capabilities if cap.enabled],
            "metrics": self.metrics
        }
    
    def get_task_status(self, task_id: str) -> Optional[TaskExecution]:
        """작업 상태 조회"""
        # 현재 실행 중인 작업 확인
        if task_id in self.current_tasks:
            return self.current_tasks[task_id]
        
        # 완료된 작업 확인
        for task in self.completed_tasks:
            if task.task_id == task_id:
                return task
        
        return None
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.stop()