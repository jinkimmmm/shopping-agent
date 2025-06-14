"""워크플로우 엔진 - 워크플로우 실행 및 관리"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from enum import Enum

from .workflow_models import (
    Workflow, WorkflowStep, WorkflowExecution, WorkflowStatus,
    StepStatus, StepType, ExecutionResult, TriggerType
)
from agents.base_agent import BaseAgent
from ai.agent_nlp_handler import AgentTask, TaskType
from core.logger import log_function_call
from core.config import get_config


class WorkflowEngine:
    """워크플로우 실행 엔진"""
    
    def __init__(self):
        """워크플로우 엔진 초기화"""
        self.settings = get_config()
        
        # 워크플로우 저장소
        self.workflows: Dict[str, Workflow] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        
        # 에이전트 레지스트리
        self.agents: Dict[str, BaseAgent] = {}
        
        # 실행 상태
        self.running_executions: Set[str] = set()
        self.execution_tasks: Dict[str, asyncio.Task] = {}
        
        # 스텝 실행기 매핑
        self.step_executors: Dict[StepType, Callable] = {
            StepType.TASK: self._execute_task_step,
            StepType.CONDITION: self._execute_condition_step,
            StepType.PARALLEL: self._execute_parallel_step,
            StepType.SEQUENTIAL: self._execute_sequential_step,
            StepType.LOOP: self._execute_loop_step,
            StepType.WAIT: self._execute_wait_step,
            StepType.APPROVAL: self._execute_approval_step,
            StepType.NOTIFICATION: self._execute_notification_step,
            StepType.DATA_TRANSFORM: self._execute_data_transform_step,
            StepType.API_CALL: self._execute_api_call_step,
            StepType.HUMAN_INPUT: self._execute_human_input_step
        }
        
        # 이벤트 핸들러
        self.event_handlers: Dict[str, List[Callable]] = {
            "workflow_started": [],
            "workflow_completed": [],
            "workflow_failed": [],
            "step_started": [],
            "step_completed": [],
            "step_failed": []
        }
        
        # 메트릭
        self.metrics = {
            "total_workflows": 0,
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "active_executions": 0
        }
    
    def register_agent(self, agent: BaseAgent) -> None:
        """에이전트 등록"""
        self.agents[agent.agent_type.value] = agent
    
    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """이벤트 핸들러 등록"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """이벤트 발생"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    print(f"이벤트 핸들러 실행 실패: {e}")
    
    @log_function_call
    async def create_workflow(self, workflow: Workflow) -> bool:
        """워크플로우 생성"""
        try:
            # 유효성 검사
            errors = workflow.validate()
            if errors:
                raise ValueError(f"워크플로우 유효성 검사 실패: {', '.join(errors)}")
            
            # 워크플로우 저장
            self.workflows[workflow.workflow_id] = workflow
            self.metrics["total_workflows"] += 1
            
            return True
            
        except Exception as e:
            print(f"워크플로우 생성 실패: {e}")
            return False
    
    @log_function_call
    async def start_workflow(
        self, 
        workflow_id: str, 
        trigger_data: Dict[str, Any] = None,
        triggered_by: str = "manual"
    ) -> Optional[str]:
        """워크플로우 실행 시작"""
        try:
            workflow = self.workflows.get(workflow_id)
            if not workflow:
                raise ValueError(f"워크플로우를 찾을 수 없음: {workflow_id}")
            
            if workflow.status != WorkflowStatus.ACTIVE:
                raise ValueError(f"워크플로우가 활성 상태가 아님: {workflow.status.value}")
            
            # 동시 실행 제한 확인
            active_count = sum(
                1 for exec in self.executions.values()
                if exec.workflow_id == workflow_id and exec.status == WorkflowStatus.RUNNING
            )
            
            if active_count >= workflow.max_concurrent_executions:
                raise ValueError(f"최대 동시 실행 수 초과: {active_count}/{workflow.max_concurrent_executions}")
            
            # 실행 인스턴스 생성
            execution = WorkflowExecution(
                execution_id=f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                workflow_id=workflow_id,
                workflow_version=workflow.version,
                triggered_by=triggered_by,
                trigger_data=trigger_data or {},
                total_steps=len(workflow.steps)
            )
            
            # 워크플로우 변수를 컨텍스트에 추가
            for var in workflow.variables:
                execution.context[var.name] = var.value
            
            # 트리거 데이터를 컨텍스트에 추가
            execution.context.update(trigger_data or {})
            
            # 실행 저장
            self.executions[execution.execution_id] = execution
            self.running_executions.add(execution.execution_id)
            self.metrics["total_executions"] += 1
            self.metrics["active_executions"] += 1
            
            # 이벤트 발생
            await self._emit_event("workflow_started", {
                "execution_id": execution.execution_id,
                "workflow_id": workflow_id,
                "triggered_by": triggered_by
            })
            
            # 비동기 실행 시작
            task = asyncio.create_task(self._execute_workflow(execution, workflow))
            self.execution_tasks[execution.execution_id] = task
            
            return execution.execution_id
            
        except Exception as e:
            print(f"워크플로우 시작 실패: {e}")
            return None
    
    async def _execute_workflow(self, execution: WorkflowExecution, workflow: Workflow) -> None:
        """워크플로우 실행"""
        try:
            # 실행 순서 계산
            execution_levels = workflow.get_execution_order()
            
            for level in execution_levels:
                # 현재 레벨의 스텝들을 병렬 실행
                level_tasks = []
                
                for step_id in level:
                    step = workflow.get_step(step_id)
                    if step and step.can_execute(execution.get_completed_step_ids(), execution.context):
                        task = asyncio.create_task(self._execute_step(step, execution, workflow))
                        level_tasks.append(task)
                
                # 현재 레벨의 모든 스텝 완료 대기
                if level_tasks:
                    await asyncio.gather(*level_tasks, return_exceptions=True)
                
                # 실패한 스텝이 있는지 확인
                failed_steps = [
                    step_id for step_id in level
                    if execution.get_step_result(step_id) and not execution.get_step_result(step_id).success
                ]
                
                if failed_steps and not workflow.retry_failed_executions:
                    # 실패 시 워크플로우 중단
                    execution.status = WorkflowStatus.FAILED
                    break
            
            # 실행 완료 처리
            await self._complete_workflow_execution(execution, workflow)
            
        except Exception as e:
            print(f"워크플로우 실행 실패: {e}")
            execution.status = WorkflowStatus.FAILED
            await self._complete_workflow_execution(execution, workflow)
    
    async def _execute_step(
        self, 
        step: WorkflowStep, 
        execution: WorkflowExecution, 
        workflow: Workflow
    ) -> None:
        """스텝 실행"""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now()
        step.attempt_count += 1
        
        # 이벤트 발생
        await self._emit_event("step_started", {
            "execution_id": execution.execution_id,
            "step_id": step.step_id,
            "step_name": step.name
        })
        
        try:
            # 타임아웃 설정
            timeout = step.timeout_seconds or 300  # 기본 5분
            
            # 스텝 실행
            executor = self.step_executors.get(step.step_type)
            if not executor:
                raise ValueError(f"지원하지 않는 스텝 유형: {step.step_type.value}")
            
            result = await asyncio.wait_for(
                executor(step, execution, workflow),
                timeout=timeout
            )
            
            # 결과 저장
            step.result = result
            step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
            step.completed_at = datetime.now()
            
            # 실행 결과 추가
            execution.add_step_result(step.step_id, result)
            
            # 이벤트 발생
            event_type = "step_completed" if result.success else "step_failed"
            await self._emit_event(event_type, {
                "execution_id": execution.execution_id,
                "step_id": step.step_id,
                "step_name": step.name,
                "result": result.to_dict()
            })
            
        except asyncio.TimeoutError:
            step.status = StepStatus.FAILED
            step.completed_at = datetime.now()
            
            result = ExecutionResult(
                success=False,
                error_message=f"스텝 실행 타임아웃: {timeout}초"
            )
            step.result = result
            execution.add_step_result(step.step_id, result)
            
            await self._emit_event("step_failed", {
                "execution_id": execution.execution_id,
                "step_id": step.step_id,
                "step_name": step.name,
                "error": "timeout"
            })
            
        except Exception as e:
            step.status = StepStatus.FAILED
            step.completed_at = datetime.now()
            
            # 재시도 확인
            if step.should_retry(e):
                step.status = StepStatus.RETRY
                delay = step.get_retry_delay()
                
                # 재시도 지연
                if delay > 0:
                    await asyncio.sleep(delay)
                
                # 재시도 실행
                await self._execute_step(step, execution, workflow)
                return
            
            result = ExecutionResult(
                success=False,
                error_message=str(e)
            )
            step.result = result
            execution.add_step_result(step.step_id, result)
            
            await self._emit_event("step_failed", {
                "execution_id": execution.execution_id,
                "step_id": step.step_id,
                "step_name": step.name,
                "error": str(e)
            })
    
    async def _execute_task_step(
        self, 
        step: WorkflowStep, 
        execution: WorkflowExecution, 
        workflow: Workflow
    ) -> ExecutionResult:
        """작업 스텝 실행"""
        agent_type = step.agent_type or "worker"
        agent = self.agents.get(agent_type)
        
        if not agent:
            return ExecutionResult(
                success=False,
                error_message=f"에이전트를 찾을 수 없음: {agent_type}"
            )
        
        # 에이전트 작업 생성
        task = AgentTask(
            task_id=f"workflow_{execution.execution_id}_{step.step_id}",
            task_type=TaskType(step.parameters.get("task_type", "general")),
            description=step.description,
            parameters=step.parameters,
            priority=step.parameters.get("priority", 1)
        )
        
        # 컨텍스트 데이터 추가
        task.parameters["context"] = execution.context
        
        try:
            # 에이전트에 작업 할당
            await agent.add_task(task)
            
            # 작업 완료 대기 (간단한 구현)
            # 실제 구현에서는 더 정교한 작업 상태 추적 필요
            await asyncio.sleep(1)  # 작업 처리 시간 시뮬레이션
            
            # 결과 시뮬레이션 (실제 구현에서는 에이전트로부터 결과 수신)
            result_data = {
                "task_id": task.task_id,
                "agent_type": agent_type,
                "processed_at": datetime.now().isoformat()
            }
            
            return ExecutionResult(
                success=True,
                data=result_data,
                execution_time=1.0
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=f"작업 실행 실패: {e}"
            )
    
    async def _execute_condition_step(
        self, 
        step: WorkflowStep, 
        execution: WorkflowExecution, 
        workflow: Workflow
    ) -> ExecutionResult:
        """조건 스텝 실행"""
        condition_expr = step.parameters.get("condition", "true")
        
        try:
            # 조건 평가
            result = eval(condition_expr, {"__builtins__": {}}, execution.context)
            
            return ExecutionResult(
                success=True,
                data={"condition_result": bool(result)},
                execution_time=0.1
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=f"조건 평가 실패: {e}"
            )
    
    async def _execute_parallel_step(
        self, 
        step: WorkflowStep, 
        execution: WorkflowExecution, 
        workflow: Workflow
    ) -> ExecutionResult:
        """병렬 스텝 실행"""
        parallel_steps = step.parameters.get("steps", [])
        
        if not parallel_steps:
            return ExecutionResult(
                success=False,
                error_message="병렬 실행할 스텝이 없음"
            )
        
        try:
            # 병렬 스텝들을 동시 실행
            tasks = []
            for step_id in parallel_steps:
                parallel_step = workflow.get_step(step_id)
                if parallel_step:
                    task = asyncio.create_task(
                        self._execute_step(parallel_step, execution, workflow)
                    )
                    tasks.append(task)
            
            # 모든 병렬 스텝 완료 대기
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 수집
            results = []
            for step_id in parallel_steps:
                step_result = execution.get_step_result(step_id)
                if step_result:
                    results.append(step_result.to_dict())
            
            return ExecutionResult(
                success=True,
                data={"parallel_results": results},
                execution_time=max(r.get("execution_time", 0) for r in results) if results else 0
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=f"병렬 실행 실패: {e}"
            )
    
    async def _execute_sequential_step(
        self, 
        step: WorkflowStep, 
        execution: WorkflowExecution, 
        workflow: Workflow
    ) -> ExecutionResult:
        """순차 스텝 실행"""
        sequential_steps = step.parameters.get("steps", [])
        
        if not sequential_steps:
            return ExecutionResult(
                success=False,
                error_message="순차 실행할 스텝이 없음"
            )
        
        try:
            results = []
            total_time = 0.0
            
            # 순차적으로 스텝 실행
            for step_id in sequential_steps:
                sequential_step = workflow.get_step(step_id)
                if sequential_step:
                    await self._execute_step(sequential_step, execution, workflow)
                    
                    step_result = execution.get_step_result(step_id)
                    if step_result:
                        results.append(step_result.to_dict())
                        total_time += step_result.execution_time
                        
                        # 실패 시 중단
                        if not step_result.success:
                            break
            
            return ExecutionResult(
                success=all(r.get("success", False) for r in results),
                data={"sequential_results": results},
                execution_time=total_time
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=f"순차 실행 실패: {e}"
            )
    
    async def _execute_loop_step(
        self, 
        step: WorkflowStep, 
        execution: WorkflowExecution, 
        workflow: Workflow
    ) -> ExecutionResult:
        """루프 스텝 실행"""
        loop_condition = step.parameters.get("condition", "false")
        loop_steps = step.parameters.get("steps", [])
        max_iterations = step.parameters.get("max_iterations", 10)
        
        try:
            results = []
            iteration = 0
            total_time = 0.0
            
            while iteration < max_iterations:
                # 루프 조건 확인
                try:
                    should_continue = eval(loop_condition, {"__builtins__": {}}, {
                        **execution.context,
                        "iteration": iteration
                    })
                    
                    if not should_continue:
                        break
                        
                except Exception:
                    break
                
                # 루프 스텝들 실행
                iteration_results = []
                for step_id in loop_steps:
                    loop_step = workflow.get_step(step_id)
                    if loop_step:
                        await self._execute_step(loop_step, execution, workflow)
                        
                        step_result = execution.get_step_result(step_id)
                        if step_result:
                            iteration_results.append(step_result.to_dict())
                            total_time += step_result.execution_time
                
                results.append({
                    "iteration": iteration,
                    "results": iteration_results
                })
                
                iteration += 1
            
            return ExecutionResult(
                success=True,
                data={
                    "loop_results": results,
                    "total_iterations": iteration
                },
                execution_time=total_time
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=f"루프 실행 실패: {e}"
            )
    
    async def _execute_wait_step(
        self, 
        step: WorkflowStep, 
        execution: WorkflowExecution, 
        workflow: Workflow
    ) -> ExecutionResult:
        """대기 스텝 실행"""
        wait_seconds = step.parameters.get("seconds", 1)
        
        try:
            await asyncio.sleep(wait_seconds)
            
            return ExecutionResult(
                success=True,
                data={"waited_seconds": wait_seconds},
                execution_time=wait_seconds
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=f"대기 실행 실패: {e}"
            )
    
    async def _execute_approval_step(
        self, 
        step: WorkflowStep, 
        execution: WorkflowExecution, 
        workflow: Workflow
    ) -> ExecutionResult:
        """승인 스텝 실행 (시뮬레이션)"""
        approval_message = step.parameters.get("message", "승인이 필요합니다")
        auto_approve = step.parameters.get("auto_approve", True)  # 테스트용
        
        try:
            if auto_approve:
                # 자동 승인 (테스트용)
                await asyncio.sleep(0.5)
                approved = True
            else:
                # 실제 구현에서는 외부 승인 시스템과 연동
                approved = False
            
            return ExecutionResult(
                success=approved,
                data={
                    "approval_message": approval_message,
                    "approved": approved,
                    "approved_at": datetime.now().isoformat() if approved else None
                },
                execution_time=0.5
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=f"승인 처리 실패: {e}"
            )
    
    async def _execute_notification_step(
        self, 
        step: WorkflowStep, 
        execution: WorkflowExecution, 
        workflow: Workflow
    ) -> ExecutionResult:
        """알림 스텝 실행"""
        message = step.parameters.get("message", "")
        recipients = step.parameters.get("recipients", [])
        notification_type = step.parameters.get("type", "email")
        
        try:
            # 알림 발송 시뮬레이션
            print(f"알림 발송: {notification_type} - {message} -> {recipients}")
            
            return ExecutionResult(
                success=True,
                data={
                    "message": message,
                    "recipients": recipients,
                    "notification_type": notification_type,
                    "sent_at": datetime.now().isoformat()
                },
                execution_time=0.2
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=f"알림 발송 실패: {e}"
            )
    
    async def _execute_data_transform_step(
        self, 
        step: WorkflowStep, 
        execution: WorkflowExecution, 
        workflow: Workflow
    ) -> ExecutionResult:
        """데이터 변환 스텝 실행"""
        transform_script = step.parameters.get("script", "")
        input_data = step.parameters.get("input_data", {})
        
        try:
            # 데이터 변환 실행
            # 실제 구현에서는 안전한 스크립트 실행 환경 사용
            local_vars = {
                **execution.context,
                **input_data,
                "input": input_data
            }
            
            exec(transform_script, {"__builtins__": {}}, local_vars)
            
            # 결과 추출
            output_data = local_vars.get("output", {})
            
            return ExecutionResult(
                success=True,
                data=output_data,
                execution_time=0.1
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=f"데이터 변환 실패: {e}"
            )
    
    async def _execute_api_call_step(
        self, 
        step: WorkflowStep, 
        execution: WorkflowExecution, 
        workflow: Workflow
    ) -> ExecutionResult:
        """API 호출 스텝 실행"""
        url = step.parameters.get("url", "")
        method = step.parameters.get("method", "GET")
        headers = step.parameters.get("headers", {})
        data = step.parameters.get("data", {})
        
        try:
            # API 호출 시뮬레이션
            # 실제 구현에서는 httpx 또는 aiohttp 사용
            await asyncio.sleep(0.5)  # 네트워크 지연 시뮬레이션
            
            # 시뮬레이션 응답
            response_data = {
                "status_code": 200,
                "response": {"message": "API 호출 성공", "data": data}
            }
            
            return ExecutionResult(
                success=True,
                data=response_data,
                execution_time=0.5
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=f"API 호출 실패: {e}"
            )
    
    async def _execute_human_input_step(
        self, 
        step: WorkflowStep, 
        execution: WorkflowExecution, 
        workflow: Workflow
    ) -> ExecutionResult:
        """사용자 입력 스텝 실행 (시뮬레이션)"""
        prompt_message = step.parameters.get("prompt", "입력이 필요합니다")
        input_type = step.parameters.get("input_type", "text")
        auto_input = step.parameters.get("auto_input", "테스트 입력")  # 테스트용
        
        try:
            # 사용자 입력 시뮬레이션
            print(f"사용자 입력 요청: {prompt_message}")
            
            # 자동 입력 (테스트용)
            user_input = auto_input
            
            return ExecutionResult(
                success=True,
                data={
                    "prompt": prompt_message,
                    "input_type": input_type,
                    "user_input": user_input,
                    "input_at": datetime.now().isoformat()
                },
                execution_time=1.0
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=f"사용자 입력 처리 실패: {e}"
            )
    
    async def _complete_workflow_execution(
        self, 
        execution: WorkflowExecution, 
        workflow: Workflow
    ) -> None:
        """워크플로우 실행 완료 처리"""
        execution.completed_at = datetime.now()
        
        # 최종 상태 결정
        if execution.status == WorkflowStatus.RUNNING:
            if execution.failed_steps > 0:
                execution.status = WorkflowStatus.FAILED
            else:
                execution.status = WorkflowStatus.COMPLETED
        
        # 실행 상태 업데이트
        self.running_executions.discard(execution.execution_id)
        self.metrics["active_executions"] -= 1
        
        if execution.status == WorkflowStatus.COMPLETED:
            self.metrics["successful_executions"] += 1
        else:
            self.metrics["failed_executions"] += 1
        
        # 평균 실행 시간 업데이트
        duration = execution.get_duration()
        if duration:
            current_avg = self.metrics["average_execution_time"]
            total_executions = self.metrics["successful_executions"] + self.metrics["failed_executions"]
            
            self.metrics["average_execution_time"] = (
                (current_avg * (total_executions - 1) + duration.total_seconds()) / total_executions
            )
        
        # 실행 태스크 정리
        if execution.execution_id in self.execution_tasks:
            del self.execution_tasks[execution.execution_id]
        
        # 이벤트 발생
        event_type = "workflow_completed" if execution.status == WorkflowStatus.COMPLETED else "workflow_failed"
        await self._emit_event(event_type, {
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "duration": duration.total_seconds() if duration else None
        })
    
    @log_function_call
    async def stop_workflow(self, execution_id: str) -> bool:
        """워크플로우 실행 중단"""
        try:
            execution = self.executions.get(execution_id)
            if not execution:
                return False
            
            if execution_id in self.execution_tasks:
                # 실행 태스크 취소
                task = self.execution_tasks[execution_id]
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # 상태 업데이트
            execution.status = WorkflowStatus.CANCELLED
            execution.completed_at = datetime.now()
            
            # 정리
            self.running_executions.discard(execution_id)
            self.metrics["active_executions"] -= 1
            
            if execution_id in self.execution_tasks:
                del self.execution_tasks[execution_id]
            
            return True
            
        except Exception as e:
            print(f"워크플로우 중단 실패: {e}")
            return False
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """워크플로우 조회"""
        return self.workflows.get(workflow_id)
    
    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """실행 인스턴스 조회"""
        return self.executions.get(execution_id)
    
    def list_workflows(self) -> List[Workflow]:
        """워크플로우 목록 조회"""
        return list(self.workflows.values())
    
    def list_executions(self, workflow_id: str = None) -> List[WorkflowExecution]:
        """실행 인스턴스 목록 조회"""
        executions = list(self.executions.values())
        
        if workflow_id:
            executions = [ex for ex in executions if ex.workflow_id == workflow_id]
        
        return sorted(executions, key=lambda x: x.started_at, reverse=True)
    
    def get_metrics(self) -> Dict[str, Any]:
        """메트릭 조회"""
        return self.metrics.copy()
    
    async def cleanup_completed_executions(self, max_age_days: int = 30) -> int:
        """완료된 실행 인스턴스 정리"""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        to_remove = []
        for execution_id, execution in self.executions.items():
            if (execution.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED] and
                execution.completed_at and execution.completed_at < cutoff_date):
                to_remove.append(execution_id)
        
        for execution_id in to_remove:
            del self.executions[execution_id]
        
        return len(to_remove)
    
    async def shutdown(self):
        """워크플로우 엔진 종료"""
        # 실행 중인 모든 작업 취소
        for task in self.execution_tasks.values():
            if not task.done():
                task.cancel()
        
        # 모든 작업이 완료될 때까지 대기
        if self.execution_tasks:
            await asyncio.gather(*self.execution_tasks.values(), return_exceptions=True)
        
        # 상태 초기화
        self.running_executions.clear()
        self.execution_tasks.clear()