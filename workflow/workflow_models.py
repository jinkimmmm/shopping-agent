"""워크플로우 모델 정의"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, field


class StepType(Enum):
    """워크플로우 스텝 유형"""
    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    LOOP = "loop"
    WAIT = "wait"
    APPROVAL = "approval"
    NOTIFICATION = "notification"
    DATA_TRANSFORM = "data_transform"
    API_CALL = "api_call"
    HUMAN_INPUT = "human_input"


class StepStatus(Enum):
    """스텝 실행 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"
    CANCELLED = "cancelled"
    RETRY = "retry"


class WorkflowStatus(Enum):
    """워크플로우 상태"""
    DRAFT = "draft"
    ACTIVE = "active"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class TriggerType(Enum):
    """워크플로우 트리거 유형"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"
    API = "api"
    WEBHOOK = "webhook"
    FILE_CHANGE = "file_change"
    EMAIL = "email"


@dataclass
class ExecutionResult:
    """실행 결과"""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }


@dataclass
class StepCondition:
    """스텝 실행 조건"""
    expression: str
    variables: Dict[str, Any] = field(default_factory=dict)
    operator: str = "and"  # and, or, not
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """조건 평가"""
        try:
            # 간단한 조건 평가 (실제 구현에서는 더 안전한 평가기 사용)
            local_vars = {**self.variables, **context}
            return eval(self.expression, {"__builtins__": {}}, local_vars)
        except Exception:
            return False


@dataclass
class StepRetryConfig:
    """스텝 재시도 설정"""
    max_attempts: int = 3
    delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 60.0
    retry_on_errors: List[str] = field(default_factory=list)


@dataclass
class WorkflowStep:
    """워크플로우 스텝"""
    step_id: str
    name: str
    step_type: StepType
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    condition: Optional[StepCondition] = None
    retry_config: Optional[StepRetryConfig] = None
    timeout_seconds: Optional[int] = None
    agent_type: Optional[str] = None  # 실행할 에이전트 유형
    
    # 실행 상태
    status: StepStatus = StepStatus.PENDING
    result: Optional[ExecutionResult] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempt_count: int = 0
    
    def __post_init__(self):
        if not self.step_id:
            self.step_id = str(uuid.uuid4())
    
    def can_execute(self, completed_steps: List[str], context: Dict[str, Any]) -> bool:
        """실행 가능 여부 확인"""
        # 의존성 확인
        if self.dependencies:
            if not all(dep in completed_steps for dep in self.dependencies):
                return False
        
        # 조건 확인
        if self.condition:
            if not self.condition.evaluate(context):
                return False
        
        return True
    
    def should_retry(self, error: Exception) -> bool:
        """재시도 여부 확인"""
        if not self.retry_config:
            return False
        
        if self.attempt_count >= self.retry_config.max_attempts:
            return False
        
        if self.retry_config.retry_on_errors:
            error_type = type(error).__name__
            if error_type not in self.retry_config.retry_on_errors:
                return False
        
        return True
    
    def get_retry_delay(self) -> float:
        """재시도 지연 시간 계산"""
        if not self.retry_config:
            return 0.0
        
        delay = self.retry_config.delay_seconds * (
            self.retry_config.backoff_multiplier ** (self.attempt_count - 1)
        )
        
        return min(delay, self.retry_config.max_delay_seconds)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "step_type": self.step_type.value,
            "description": self.description,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "condition": {
                "expression": self.condition.expression,
                "variables": self.condition.variables,
                "operator": self.condition.operator
            } if self.condition else None,
            "retry_config": {
                "max_attempts": self.retry_config.max_attempts,
                "delay_seconds": self.retry_config.delay_seconds,
                "backoff_multiplier": self.retry_config.backoff_multiplier,
                "max_delay_seconds": self.retry_config.max_delay_seconds,
                "retry_on_errors": self.retry_config.retry_on_errors
            } if self.retry_config else None,
            "timeout_seconds": self.timeout_seconds,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "result": self.result.to_dict() if self.result else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "attempt_count": self.attempt_count
        }


@dataclass
class WorkflowTrigger:
    """워크플로우 트리거"""
    trigger_type: TriggerType
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trigger_type": self.trigger_type.value,
            "config": self.config,
            "enabled": self.enabled
        }


@dataclass
class WorkflowVariable:
    """워크플로우 변수"""
    name: str
    value: Any
    variable_type: str = "string"  # string, number, boolean, object, array
    description: str = ""
    required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "variable_type": self.variable_type,
            "description": self.description,
            "required": self.required
        }


@dataclass
class Workflow:
    """워크플로우 정의"""
    workflow_id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    steps: List[WorkflowStep] = field(default_factory=list)
    variables: List[WorkflowVariable] = field(default_factory=list)
    triggers: List[WorkflowTrigger] = field(default_factory=list)
    
    # 메타데이터
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    tags: List[str] = field(default_factory=list)
    
    # 실행 설정
    timeout_minutes: Optional[int] = None
    max_concurrent_executions: int = 1
    retry_failed_executions: bool = False
    
    def __post_init__(self):
        if not self.workflow_id:
            self.workflow_id = str(uuid.uuid4())
    
    def add_step(self, step: WorkflowStep) -> None:
        """스텝 추가"""
        self.steps.append(step)
        self.updated_at = datetime.now()
    
    def remove_step(self, step_id: str) -> bool:
        """스텝 제거"""
        for i, step in enumerate(self.steps):
            if step.step_id == step_id:
                del self.steps[i]
                self.updated_at = datetime.now()
                return True
        return False
    
    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """스텝 조회"""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def get_executable_steps(self, completed_steps: List[str], context: Dict[str, Any]) -> List[WorkflowStep]:
        """실행 가능한 스텝 목록 조회"""
        executable = []
        
        for step in self.steps:
            if step.status == StepStatus.PENDING and step.can_execute(completed_steps, context):
                executable.append(step)
        
        return executable
    
    def get_variable_value(self, name: str, default: Any = None) -> Any:
        """변수 값 조회"""
        for var in self.variables:
            if var.name == name:
                return var.value
        return default
    
    def set_variable_value(self, name: str, value: Any) -> None:
        """변수 값 설정"""
        for var in self.variables:
            if var.name == name:
                var.value = value
                self.updated_at = datetime.now()
                return
        
        # 새 변수 추가
        self.variables.append(WorkflowVariable(name=name, value=value))
        self.updated_at = datetime.now()
    
    def validate(self) -> List[str]:
        """워크플로우 유효성 검사"""
        errors = []
        
        # 기본 검사
        if not self.name:
            errors.append("워크플로우 이름이 필요합니다")
        
        if not self.steps:
            errors.append("최소 하나의 스텝이 필요합니다")
        
        # 스텝 ID 중복 검사
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            errors.append("스텝 ID가 중복됩니다")
        
        # 의존성 검사
        for step in self.steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    errors.append(f"스텝 '{step.name}'의 의존성 '{dep}'를 찾을 수 없습니다")
        
        # 순환 의존성 검사
        if self._has_circular_dependency():
            errors.append("순환 의존성이 발견되었습니다")
        
        # 필수 변수 검사
        required_vars = [var.name for var in self.variables if var.required]
        for var_name in required_vars:
            var_value = self.get_variable_value(var_name)
            if var_value is None:
                errors.append(f"필수 변수 '{var_name}'의 값이 설정되지 않았습니다")
        
        return errors
    
    def _has_circular_dependency(self) -> bool:
        """순환 의존성 검사"""
        def visit(step_id: str, visited: set, rec_stack: set) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)
            
            step = self.get_step(step_id)
            if step:
                for dep in step.dependencies:
                    if dep not in visited:
                        if visit(dep, visited, rec_stack):
                            return True
                    elif dep in rec_stack:
                        return True
            
            rec_stack.remove(step_id)
            return False
        
        visited = set()
        for step in self.steps:
            if step.step_id not in visited:
                if visit(step.step_id, visited, set()):
                    return True
        
        return False
    
    def get_execution_order(self) -> List[List[str]]:
        """실행 순서 계산 (위상 정렬)"""
        # 의존성 그래프 구성
        in_degree = {step.step_id: 0 for step in self.steps}
        graph = {step.step_id: [] for step in self.steps}
        
        for step in self.steps:
            for dep in step.dependencies:
                if dep in graph:
                    graph[dep].append(step.step_id)
                    in_degree[step.step_id] += 1
        
        # 위상 정렬
        levels = []
        queue = [step_id for step_id, degree in in_degree.items() if degree == 0]
        
        while queue:
            current_level = queue[:]
            levels.append(current_level)
            queue = []
            
            for step_id in current_level:
                for neighbor in graph[step_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        
        return levels
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": [step.to_dict() for step in self.steps],
            "variables": [var.to_dict() for var in self.variables],
            "triggers": [trigger.to_dict() for trigger in self.triggers],
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
            "tags": self.tags,
            "timeout_minutes": self.timeout_minutes,
            "max_concurrent_executions": self.max_concurrent_executions,
            "retry_failed_executions": self.retry_failed_executions
        }


@dataclass
class WorkflowExecution:
    """워크플로우 실행 인스턴스"""
    execution_id: str
    workflow_id: str
    workflow_version: str
    status: WorkflowStatus = WorkflowStatus.RUNNING
    
    # 실행 정보
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    triggered_by: str = ""
    trigger_data: Dict[str, Any] = field(default_factory=dict)
    
    # 실행 컨텍스트
    context: Dict[str, Any] = field(default_factory=dict)
    step_executions: Dict[str, ExecutionResult] = field(default_factory=dict)
    
    # 메트릭
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    
    def __post_init__(self):
        if not self.execution_id:
            self.execution_id = str(uuid.uuid4())
    
    def add_step_result(self, step_id: str, result: ExecutionResult) -> None:
        """스텝 실행 결과 추가"""
        self.step_executions[step_id] = result
        
        if result.success:
            self.completed_steps += 1
            # 결과 데이터를 컨텍스트에 추가
            self.context.update(result.data)
        else:
            self.failed_steps += 1
    
    def get_step_result(self, step_id: str) -> Optional[ExecutionResult]:
        """스텝 실행 결과 조회"""
        return self.step_executions.get(step_id)
    
    def get_completed_step_ids(self) -> List[str]:
        """완료된 스텝 ID 목록"""
        return [
            step_id for step_id, result in self.step_executions.items()
            if result.success
        ]
    
    def get_progress(self) -> float:
        """진행률 계산"""
        if self.total_steps == 0:
            return 0.0
        return (self.completed_steps + self.failed_steps + self.skipped_steps) / self.total_steps
    
    def get_duration(self) -> Optional[timedelta]:
        """실행 시간 계산"""
        if self.completed_at:
            return self.completed_at - self.started_at
        return datetime.now() - self.started_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "workflow_version": self.workflow_version,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "triggered_by": self.triggered_by,
            "trigger_data": self.trigger_data,
            "context": self.context,
            "step_executions": {
                step_id: result.to_dict()
                for step_id, result in self.step_executions.items()
            },
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "progress": self.get_progress(),
            "duration_seconds": self.get_duration().total_seconds() if self.get_duration() else None
        }