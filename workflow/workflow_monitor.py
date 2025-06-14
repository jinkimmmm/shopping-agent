"""워크플로우 모니터링 시스템"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, asdict

from .workflow_models import WorkflowExecution, WorkflowStatus, StepStatus
from core.logger import log_function_call
from core.config import get_config


class MonitoringEventType(Enum):
    """모니터링 이벤트 유형"""
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_TIMEOUT = "workflow_timeout"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_TIMEOUT = "step_timeout"
    PERFORMANCE_ALERT = "performance_alert"
    RESOURCE_ALERT = "resource_alert"
    ERROR_THRESHOLD = "error_threshold"
    CUSTOM_METRIC = "custom_metric"


class AlertSeverity(Enum):
    """알림 심각도"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MonitoringEvent:
    """모니터링 이벤트"""
    event_id: str
    event_type: MonitoringEventType
    timestamp: datetime
    workflow_id: Optional[str] = None
    execution_id: Optional[str] = None
    step_id: Optional[str] = None
    severity: AlertSeverity = AlertSeverity.LOW
    message: str = ""
    data: Dict[str, Any] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        result["event_type"] = self.event_type.value
        result["severity"] = self.severity.value
        return result


@dataclass
class PerformanceMetrics:
    """성능 메트릭"""
    workflow_id: str
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    average_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    total_duration: float = 0.0
    error_rate: float = 0.0
    throughput: float = 0.0  # executions per hour
    last_execution: Optional[datetime] = None
    
    def update(self, execution: WorkflowExecution) -> None:
        """실행 결과로 메트릭 업데이트"""
        self.execution_count += 1
        self.last_execution = execution.completed_at or datetime.now()
        
        if execution.status == WorkflowStatus.COMPLETED:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        # 실행 시간 계산
        duration = execution.get_duration()
        if duration:
            duration_seconds = duration.total_seconds()
            self.total_duration += duration_seconds
            self.average_duration = self.total_duration / self.execution_count
            self.min_duration = min(self.min_duration, duration_seconds)
            self.max_duration = max(self.max_duration, duration_seconds)
        
        # 에러율 계산
        self.error_rate = self.failure_count / self.execution_count if self.execution_count > 0 else 0.0
        
        # 처리량 계산 (최근 1시간 기준)
        if self.last_execution:
            hours_since_start = max(1, (self.last_execution - (self.last_execution - timedelta(hours=1))).total_seconds() / 3600)
            self.throughput = self.execution_count / hours_since_start
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = asdict(self)
        if self.last_execution:
            result["last_execution"] = self.last_execution.isoformat()
        return result


@dataclass
class AlertRule:
    """알림 규칙"""
    rule_id: str
    name: str
    condition: str  # Python 표현식
    severity: AlertSeverity
    message_template: str
    enabled: bool = True
    cooldown_minutes: int = 5
    last_triggered: Optional[datetime] = None
    
    def should_trigger(self, context: Dict[str, Any]) -> bool:
        """알림 트리거 여부 확인"""
        if not self.enabled:
            return False
        
        # 쿨다운 확인
        if self.last_triggered:
            cooldown_delta = timedelta(minutes=self.cooldown_minutes)
            if datetime.now() - self.last_triggered < cooldown_delta:
                return False
        
        try:
            # 조건 평가
            return bool(eval(self.condition, {"__builtins__": {}}, context))
        except Exception:
            return False
    
    def format_message(self, context: Dict[str, Any]) -> str:
        """메시지 포맷팅"""
        try:
            return self.message_template.format(**context)
        except Exception:
            return self.message_template


class WorkflowMonitor:
    """워크플로우 모니터링 시스템"""
    
    def __init__(self):
        """모니터 초기화"""
        self.settings = get_config()
        
        # 이벤트 저장소
        self.events: List[MonitoringEvent] = []
        self.max_events = 10000
        
        # 성능 메트릭
        self.metrics: Dict[str, PerformanceMetrics] = {}
        
        # 알림 규칙
        self.alert_rules: Dict[str, AlertRule] = {}
        
        # 이벤트 핸들러
        self.event_handlers: Dict[MonitoringEventType, List[Callable]] = {
            event_type: [] for event_type in MonitoringEventType
        }
        
        # 모니터링 상태
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # 기본 알림 규칙 설정
        self._setup_default_alert_rules()
    
    def _setup_default_alert_rules(self) -> None:
        """기본 알림 규칙 설정"""
        default_rules = [
            AlertRule(
                rule_id="high_error_rate",
                name="높은 에러율",
                condition="error_rate > 0.1",
                severity=AlertSeverity.HIGH,
                message_template="워크플로우 {workflow_id}의 에러율이 {error_rate:.1%}로 높습니다"
            ),
            AlertRule(
                rule_id="long_execution_time",
                name="긴 실행 시간",
                condition="average_duration > 300",
                severity=AlertSeverity.MEDIUM,
                message_template="워크플로우 {workflow_id}의 평균 실행 시간이 {average_duration:.1f}초입니다"
            ),
            AlertRule(
                rule_id="workflow_failure",
                name="워크플로우 실패",
                condition="status == 'failed'",
                severity=AlertSeverity.HIGH,
                message_template="워크플로우 {workflow_id} 실행이 실패했습니다: {error_message}"
            ),
            AlertRule(
                rule_id="step_timeout",
                name="스텝 타임아웃",
                condition="step_status == 'timeout'",
                severity=AlertSeverity.MEDIUM,
                message_template="워크플로우 {workflow_id}의 스텝 {step_id}이 타임아웃되었습니다"
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.rule_id] = rule
    
    def register_event_handler(
        self, 
        event_type: MonitoringEventType, 
        handler: Callable[[MonitoringEvent], None]
    ) -> None:
        """이벤트 핸들러 등록"""
        self.event_handlers[event_type].append(handler)
    
    def add_alert_rule(self, rule: AlertRule) -> None:
        """알림 규칙 추가"""
        self.alert_rules[rule.rule_id] = rule
    
    def remove_alert_rule(self, rule_id: str) -> bool:
        """알림 규칙 제거"""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            return True
        return False
    
    @log_function_call
    async def start_monitoring(self) -> None:
        """모니터링 시작"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self) -> None:
        """모니터링 중지"""
        self.is_monitoring = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
    
    async def _monitoring_loop(self) -> None:
        """모니터링 루프"""
        while self.is_monitoring:
            try:
                # 메트릭 기반 알림 확인
                await self._check_metric_alerts()
                
                # 이벤트 정리
                await self._cleanup_old_events()
                
                # 1분마다 실행
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"모니터링 루프 오류: {e}")
                await asyncio.sleep(10)
    
    async def _check_metric_alerts(self) -> None:
        """메트릭 기반 알림 확인"""
        for workflow_id, metrics in self.metrics.items():
            context = {
                "workflow_id": workflow_id,
                **metrics.to_dict()
            }
            
            for rule in self.alert_rules.values():
                if rule.should_trigger(context):
                    await self._trigger_alert(rule, context)
    
    async def _trigger_alert(self, rule: AlertRule, context: Dict[str, Any]) -> None:
        """알림 트리거"""
        rule.last_triggered = datetime.now()
        
        event = MonitoringEvent(
            event_id=f"alert_{rule.rule_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            event_type=MonitoringEventType.PERFORMANCE_ALERT,
            timestamp=datetime.now(),
            workflow_id=context.get("workflow_id"),
            severity=rule.severity,
            message=rule.format_message(context),
            data=context,
            tags=["alert", rule.rule_id]
        )
        
        await self.record_event(event)
    
    async def _cleanup_old_events(self) -> None:
        """오래된 이벤트 정리"""
        if len(self.events) > self.max_events:
            # 오래된 이벤트 제거 (최근 이벤트만 유지)
            self.events = self.events[-self.max_events:]
    
    @log_function_call
    async def record_event(self, event: MonitoringEvent) -> None:
        """이벤트 기록"""
        # 이벤트 저장
        self.events.append(event)
        
        # 이벤트 핸들러 실행
        handlers = self.event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                print(f"이벤트 핸들러 실행 실패: {e}")
        
        # 콘솔 출력 (개발용)
        if event.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            print(f"[{event.severity.value.upper()}] {event.message}")
    
    async def record_workflow_event(
        self, 
        event_type: MonitoringEventType,
        workflow_id: str,
        execution_id: str = None,
        step_id: str = None,
        message: str = "",
        data: Dict[str, Any] = None,
        severity: AlertSeverity = AlertSeverity.LOW
    ) -> None:
        """워크플로우 이벤트 기록"""
        event = MonitoringEvent(
            event_id=f"{event_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            event_type=event_type,
            timestamp=datetime.now(),
            workflow_id=workflow_id,
            execution_id=execution_id,
            step_id=step_id,
            severity=severity,
            message=message,
            data=data or {},
            tags=["workflow"]
        )
        
        await self.record_event(event)
    
    def update_workflow_metrics(self, execution: WorkflowExecution) -> None:
        """워크플로우 메트릭 업데이트"""
        workflow_id = execution.workflow_id
        
        if workflow_id not in self.metrics:
            self.metrics[workflow_id] = PerformanceMetrics(workflow_id=workflow_id)
        
        self.metrics[workflow_id].update(execution)
    
    def get_workflow_metrics(self, workflow_id: str) -> Optional[PerformanceMetrics]:
        """워크플로우 메트릭 조회"""
        return self.metrics.get(workflow_id)
    
    def get_all_metrics(self) -> Dict[str, PerformanceMetrics]:
        """모든 메트릭 조회"""
        return self.metrics.copy()
    
    def get_events(
        self, 
        workflow_id: str = None,
        event_type: MonitoringEventType = None,
        severity: AlertSeverity = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100
    ) -> List[MonitoringEvent]:
        """이벤트 조회"""
        filtered_events = self.events
        
        # 필터링
        if workflow_id:
            filtered_events = [e for e in filtered_events if e.workflow_id == workflow_id]
        
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]
        
        if severity:
            filtered_events = [e for e in filtered_events if e.severity == severity]
        
        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]
        
        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]
        
        # 최신순 정렬 및 제한
        filtered_events.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered_events[:limit]
    
    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """알림 요약 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_events = [
            e for e in self.events 
            if e.timestamp >= cutoff_time and "alert" in e.tags
        ]
        
        # 심각도별 집계
        severity_counts = {severity.value: 0 for severity in AlertSeverity}
        for event in recent_events:
            severity_counts[event.severity.value] += 1
        
        # 워크플로우별 집계
        workflow_alerts = {}
        for event in recent_events:
            if event.workflow_id:
                if event.workflow_id not in workflow_alerts:
                    workflow_alerts[event.workflow_id] = 0
                workflow_alerts[event.workflow_id] += 1
        
        return {
            "total_alerts": len(recent_events),
            "severity_breakdown": severity_counts,
            "workflow_breakdown": workflow_alerts,
            "time_range_hours": hours
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 요약 조회"""
        if not self.metrics:
            return {
                "total_workflows": 0,
                "total_executions": 0,
                "overall_success_rate": 0.0,
                "average_duration": 0.0
            }
        
        total_executions = sum(m.execution_count for m in self.metrics.values())
        total_successes = sum(m.success_count for m in self.metrics.values())
        total_duration = sum(m.total_duration for m in self.metrics.values())
        
        return {
            "total_workflows": len(self.metrics),
            "total_executions": total_executions,
            "overall_success_rate": total_successes / total_executions if total_executions > 0 else 0.0,
            "average_duration": total_duration / total_executions if total_executions > 0 else 0.0,
            "workflows": {
                workflow_id: {
                    "executions": metrics.execution_count,
                    "success_rate": metrics.success_count / metrics.execution_count if metrics.execution_count > 0 else 0.0,
                    "average_duration": metrics.average_duration,
                    "throughput": metrics.throughput
                }
                for workflow_id, metrics in self.metrics.items()
            }
        }
    
    def export_events(
        self, 
        format_type: str = "json",
        workflow_id: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> str:
        """이벤트 내보내기"""
        events = self.get_events(
            workflow_id=workflow_id,
            start_time=start_time,
            end_time=end_time,
            limit=None
        )
        
        if format_type.lower() == "json":
            return json.dumps([event.to_dict() for event in events], indent=2, ensure_ascii=False)
        elif format_type.lower() == "csv":
            # CSV 형식으로 변환
            if not events:
                return "timestamp,event_type,workflow_id,execution_id,severity,message\n"
            
            lines = ["timestamp,event_type,workflow_id,execution_id,severity,message"]
            for event in events:
                line = f"{event.timestamp.isoformat()},{event.event_type.value},{event.workflow_id or ''},{event.execution_id or ''},{event.severity.value},\"{event.message}\""
                lines.append(line)
            
            return "\n".join(lines)
        else:
            raise ValueError(f"지원하지 않는 형식: {format_type}")
    
    async def generate_report(
        self, 
        workflow_id: str = None,
        period_hours: int = 24
    ) -> Dict[str, Any]:
        """모니터링 보고서 생성"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=period_hours)
        
        # 이벤트 조회
        events = self.get_events(
            workflow_id=workflow_id,
            start_time=start_time,
            end_time=end_time,
            limit=None
        )
        
        # 메트릭 조회
        if workflow_id:
            metrics = {workflow_id: self.get_workflow_metrics(workflow_id)} if self.get_workflow_metrics(workflow_id) else {}
        else:
            metrics = self.get_all_metrics()
        
        # 보고서 생성
        report = {
            "report_generated_at": end_time.isoformat(),
            "period": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "hours": period_hours
            },
            "summary": {
                "total_events": len(events),
                "event_types": {},
                "severity_distribution": {},
                "workflows_monitored": len(metrics)
            },
            "metrics": {wf_id: m.to_dict() for wf_id, m in metrics.items()},
            "alerts": self.get_alert_summary(period_hours),
            "performance": self.get_performance_summary()
        }
        
        # 이벤트 유형별 집계
        for event in events:
            event_type = event.event_type.value
            severity = event.severity.value
            
            if event_type not in report["summary"]["event_types"]:
                report["summary"]["event_types"][event_type] = 0
            report["summary"]["event_types"][event_type] += 1
            
            if severity not in report["summary"]["severity_distribution"]:
                report["summary"]["severity_distribution"][severity] = 0
            report["summary"]["severity_distribution"][severity] += 1
        
        return report