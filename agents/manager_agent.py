"""매니저 에이전트 - 작업 조율 및 관리"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base_agent import (
    BaseAgent, AgentType, AgentStatus, AgentCapability,
    AgentTask, AgentMessage, TaskExecution, TaskStatus
)
from ai.gemini_client import GeminiClient, GenerationConfig
from ai.agent_nlp_handler import AgentNLPHandler, ParsedIntent, TaskType
from core.logger import log_function_call


class ManagerAgent(BaseAgent):
    """매니저 에이전트 - 작업 분배 및 조율 담당"""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        gemini_client: GeminiClient,
        nlp_handler: AgentNLPHandler
    ):
        """매니저 에이전트 초기화"""
        capabilities = [
            AgentCapability(
                name="task_planning",
                description="작업 계획 수립 및 분해",
                parameters={"max_subtasks": 10, "planning_depth": 3}
            ),
            AgentCapability(
                name="resource_allocation",
                description="리소스 할당 및 최적화",
                parameters={"max_workers": 5, "load_balancing": True}
            ),
            AgentCapability(
                name="progress_monitoring",
                description="진행 상황 모니터링",
                parameters={"monitoring_interval": 30, "alert_threshold": 0.8}
            ),
            AgentCapability(
                name="quality_assurance",
                description="품질 보증 및 검증",
                parameters={"validation_rules": [], "approval_required": True}
            )
        ]
        
        super().__init__(agent_id, AgentType.MANAGER, name, gemini_client, capabilities)
        
        self.nlp_handler = nlp_handler
        
        # 워커 에이전트 관리
        self.worker_agents: Dict[str, Dict[str, Any]] = {}
        self.task_assignments: Dict[str, str] = {}  # task_id -> worker_id
        
        # 작업 계획 및 실행 관리
        self.active_projects: Dict[str, Dict[str, Any]] = {}
        self.task_dependencies: Dict[str, List[str]] = {}
        
        # 성능 모니터링
        self.performance_metrics = {
            "total_projects": 0,
            "completed_projects": 0,
            "average_project_duration": 0.0,
            "worker_utilization": {},
            "task_distribution": {}
        }
    
    @log_function_call
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """작업 처리 - 매니저 역할 수행"""
        try:
            if task.task_type == TaskType.WORKFLOW_AUTOMATION:
                return await self._handle_workflow_automation(task)
            elif task.task_type == TaskType.DOCUMENT_SUMMARY:
                return await self._handle_document_summary_coordination(task)
            elif task.task_type == TaskType.DATA_ANALYSIS:
                return await self._handle_data_analysis_coordination(task)
            elif task.task_type == TaskType.CUSTOMER_SUPPORT:
                return await self._handle_customer_support_coordination(task)
            elif task.task_type == TaskType.CODE_ASSISTANCE:
                return await self._handle_code_assistance_coordination(task)
            else:
                return await self._handle_general_coordination(task)
                
        except Exception as e:
            self.logger.error(f"매니저 작업 처리 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _handle_workflow_automation(self, task: AgentTask) -> Dict[str, Any]:
        """워크플로우 자동화 처리"""
        self.logger.info(f"워크플로우 자동화 시작: {task.task_id}")
        
        # 1. 워크플로우 분석
        workflow_analysis = await self._analyze_workflow(task)
        
        # 2. 작업 분해
        subtasks = await self._decompose_workflow(task, workflow_analysis)
        
        # 3. 리소스 할당
        assignments = await self._allocate_resources(subtasks)
        
        # 4. 실행 계획 수립
        execution_plan = await self._create_execution_plan(subtasks, assignments)
        
        # 5. 프로젝트 등록
        project_id = f"project_{task.task_id}"
        self.active_projects[project_id] = {
            "task_id": task.task_id,
            "subtasks": subtasks,
            "assignments": assignments,
            "execution_plan": execution_plan,
            "start_time": datetime.now(),
            "status": "in_progress"
        }
        
        # 6. 워커에게 작업 분배
        distribution_results = await self._distribute_tasks(subtasks, assignments)
        
        return {
            "success": True,
            "project_id": project_id,
            "subtasks_count": len(subtasks),
            "assigned_workers": list(assignments.values()),
            "distribution_results": distribution_results,
            "execution_plan": execution_plan
        }
    
    async def _analyze_workflow(self, task: AgentTask) -> Dict[str, Any]:
        """워크플로우 분석"""
        prompt = f"""
다음 워크플로우 자동화 요청을 분석해주세요:

작업 설명: {task.description}
매개변수: {json.dumps(task.parameters, ensure_ascii=False)}

분석 결과를 다음 형식으로 제공해주세요:
{{
  "workflow_type": "워크플로우 유형",
  "complexity": "복잡도 (low/medium/high)",
  "estimated_duration": "예상 소요 시간 (분)",
  "required_skills": ["필요한 기술들"],
  "dependencies": ["의존성들"],
  "risks": ["위험 요소들"]
}}
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.3, max_output_tokens=800)
            )
            
            return json.loads(response)
            
        except Exception as e:
            self.logger.error(f"워크플로우 분석 실패: {e}")
            return {
                "workflow_type": "unknown",
                "complexity": "medium",
                "estimated_duration": 60,
                "required_skills": [],
                "dependencies": [],
                "risks": []
            }
    
    async def _decompose_workflow(self, task: AgentTask, analysis: Dict[str, Any]) -> List[AgentTask]:
        """워크플로우 작업 분해"""
        prompt = f"""
다음 워크플로우를 실행 가능한 하위 작업들로 분해해주세요:

원본 작업: {task.description}
분석 결과: {json.dumps(analysis, ensure_ascii=False)}

각 하위 작업을 다음 형식으로 제공해주세요:
{{
  "subtasks": [
    {{
      "task_id": "고유_ID",
      "task_type": "작업_유형",
      "description": "작업_설명",
      "parameters": {{"매개변수": "값"}},
      "priority": 1,
      "dependencies": ["의존_작업_ID"],
      "estimated_duration": 30,
      "required_skills": ["필요_기술"]
    }}
  ]
}}
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.3, max_output_tokens=1500)
            )
            
            result = json.loads(response)
            subtasks = []
            
            for subtask_data in result.get("subtasks", []):
                subtask = AgentTask(
                    task_id=subtask_data.get("task_id", f"subtask_{len(subtasks)}"),
                    task_type=TaskType(subtask_data.get("task_type", "general_chat")),
                    description=subtask_data.get("description", ""),
                    parameters=subtask_data.get("parameters", {}),
                    priority=subtask_data.get("priority", 1),
                    dependencies=subtask_data.get("dependencies", [])
                )
                subtasks.append(subtask)
            
            return subtasks
            
        except Exception as e:
            self.logger.error(f"작업 분해 실패: {e}")
            return [task]  # 원본 작업 반환
    
    async def _allocate_resources(self, subtasks: List[AgentTask]) -> Dict[str, str]:
        """리소스 할당"""
        assignments = {}
        
        # 사용 가능한 워커 조회
        available_workers = [
            worker_id for worker_id, info in self.worker_agents.items()
            if info.get("status") == "idle"
        ]
        
        if not available_workers:
            self.logger.warning("사용 가능한 워커가 없습니다")
            return assignments
        
        # 간단한 라운드 로빈 할당
        worker_index = 0
        for subtask in subtasks:
            worker_id = available_workers[worker_index % len(available_workers)]
            assignments[subtask.task_id] = worker_id
            worker_index += 1
        
        return assignments
    
    async def _create_execution_plan(self, subtasks: List[AgentTask], assignments: Dict[str, str]) -> Dict[str, Any]:
        """실행 계획 수립"""
        # 의존성 그래프 생성
        dependency_graph = {}
        for subtask in subtasks:
            dependency_graph[subtask.task_id] = subtask.dependencies
        
        # 실행 순서 결정 (토폴로지 정렬)
        execution_order = self._topological_sort(dependency_graph)
        
        # 병렬 실행 그룹 생성
        execution_groups = self._create_execution_groups(execution_order, dependency_graph)
        
        return {
            "execution_order": execution_order,
            "execution_groups": execution_groups,
            "total_estimated_duration": sum(
                subtask.parameters.get("estimated_duration", 30)
                for subtask in subtasks
            ),
            "parallel_efficiency": len(execution_groups) / len(subtasks) if subtasks else 0
        }
    
    def _topological_sort(self, dependency_graph: Dict[str, List[str]]) -> List[str]:
        """토폴로지 정렬"""
        # 간단한 토폴로지 정렬 구현
        in_degree = {node: 0 for node in dependency_graph}
        
        for node in dependency_graph:
            for dep in dependency_graph[node]:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in dependency_graph:
                if node in dependency_graph[neighbor]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        
        return result
    
    def _create_execution_groups(self, execution_order: List[str], dependency_graph: Dict[str, List[str]]) -> List[List[str]]:
        """병렬 실행 그룹 생성"""
        groups = []
        remaining = set(execution_order)
        
        while remaining:
            current_group = []
            
            for task_id in execution_order:
                if task_id not in remaining:
                    continue
                
                # 의존성이 모두 해결되었는지 확인
                dependencies_resolved = all(
                    dep not in remaining for dep in dependency_graph.get(task_id, [])
                )
                
                if dependencies_resolved:
                    current_group.append(task_id)
            
            if current_group:
                groups.append(current_group)
                remaining -= set(current_group)
            else:
                # 순환 의존성이나 오류 상황
                groups.append(list(remaining))
                break
        
        return groups
    
    async def _distribute_tasks(self, subtasks: List[AgentTask], assignments: Dict[str, str]) -> Dict[str, Any]:
        """작업 분배"""
        distribution_results = {
            "successful_assignments": 0,
            "failed_assignments": 0,
            "assignment_details": []
        }
        
        for subtask in subtasks:
            worker_id = assignments.get(subtask.task_id)
            if not worker_id:
                distribution_results["failed_assignments"] += 1
                continue
            
            try:
                # 워커에게 작업 전송 (실제로는 메시지 큐나 API 호출)
                message = AgentMessage(
                    id=f"msg_{subtask.task_id}",
                    sender_id=self.agent_id,
                    receiver_id=worker_id,
                    message_type="task_assignment",
                    content={
                        "task": {
                            "task_id": subtask.task_id,
                            "task_type": subtask.task_type.value,
                            "description": subtask.description,
                            "parameters": subtask.parameters,
                            "priority": subtask.priority,
                            "dependencies": subtask.dependencies
                        }
                    },
                    timestamp=datetime.now()
                )
                
                await self.send_message(message)
                
                # 할당 기록
                self.task_assignments[subtask.task_id] = worker_id
                
                distribution_results["successful_assignments"] += 1
                distribution_results["assignment_details"].append({
                    "task_id": subtask.task_id,
                    "worker_id": worker_id,
                    "status": "assigned"
                })
                
            except Exception as e:
                self.logger.error(f"작업 분배 실패: {subtask.task_id} -> {worker_id}: {e}")
                distribution_results["failed_assignments"] += 1
                distribution_results["assignment_details"].append({
                    "task_id": subtask.task_id,
                    "worker_id": worker_id,
                    "status": "failed",
                    "error": str(e)
                })
        
        return distribution_results
    
    async def _handle_document_summary_coordination(self, task: AgentTask) -> Dict[str, Any]:
        """문서 요약 조율"""
        # 문서 요약 작업을 적절한 워커에게 할당
        return await self._coordinate_single_task(task, "document_processing")
    
    async def _handle_data_analysis_coordination(self, task: AgentTask) -> Dict[str, Any]:
        """데이터 분석 조율"""
        # 데이터 분석 작업을 적절한 워커에게 할당
        return await self._coordinate_single_task(task, "data_analysis")
    
    async def _handle_customer_support_coordination(self, task: AgentTask) -> Dict[str, Any]:
        """고객 지원 조율"""
        # 고객 지원 작업을 적절한 워커에게 할당
        return await self._coordinate_single_task(task, "customer_service")
    
    async def _handle_code_assistance_coordination(self, task: AgentTask) -> Dict[str, Any]:
        """코드 지원 조율"""
        # 코드 지원 작업을 적절한 워커에게 할당
        return await self._coordinate_single_task(task, "code_assistance")
    
    async def _handle_general_coordination(self, task: AgentTask) -> Dict[str, Any]:
        """일반 조율"""
        # 일반 작업을 적절한 워커에게 할당
        return await self._coordinate_single_task(task, "general")
    
    async def _coordinate_single_task(self, task: AgentTask, skill_requirement: str) -> Dict[str, Any]:
        """단일 작업 조율"""
        # 적절한 워커 선택
        suitable_worker = self._find_suitable_worker(skill_requirement)
        
        if not suitable_worker:
            return {
                "success": False,
                "error": f"적절한 워커를 찾을 수 없습니다: {skill_requirement}",
                "task_id": task.task_id
            }
        
        # 작업 할당
        try:
            message = AgentMessage(
                id=f"msg_{task.task_id}",
                sender_id=self.agent_id,
                receiver_id=suitable_worker,
                message_type="task_assignment",
                content={"task": task.__dict__},
                timestamp=datetime.now()
            )
            
            await self.send_message(message)
            
            self.task_assignments[task.task_id] = suitable_worker
            
            return {
                "success": True,
                "assigned_worker": suitable_worker,
                "task_id": task.task_id,
                "skill_requirement": skill_requirement
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    def _find_suitable_worker(self, skill_requirement: str) -> Optional[str]:
        """적절한 워커 찾기"""
        # 스킬 요구사항에 맞는 유휴 워커 찾기
        for worker_id, info in self.worker_agents.items():
            if (info.get("status") == "idle" and 
                skill_requirement in info.get("skills", [])):
                return worker_id
        
        # 스킬 요구사항 무시하고 유휴 워커 찾기
        for worker_id, info in self.worker_agents.items():
            if info.get("status") == "idle":
                return worker_id
        
        return None
    
    @log_function_call
    async def process_request(self, request: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """사용자 요청 직접 처리"""
        try:
            self.logger.info(f"매니저 에이전트 요청 처리 시작: {request[:100]}...")
            
            # NLP 처리로 사용자 의도 파악
            parsed_intent = await self.nlp_handler.parse_user_input(request)
            
            # 쇼핑 관련 요청인지 확인하고 적절한 응답 생성
            if "가격" in request or "쇼핑" in request or "비교" in request:
                response = await self._handle_shopping_request(request, parsed_intent)
            else:
                # 일반적인 요청 처리
                response = await self._handle_general_request(request, parsed_intent)
            
            self.logger.info("매니저 에이전트 요청 처리 완료")
            return response
            
        except Exception as e:
            self.logger.error(f"매니저 에이전트 요청 처리 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_shopping_request(self, request: str, parsed_intent: ParsedIntent) -> Dict[str, Any]:
        """쇼핑 관련 요청 처리"""
        prompt = f"""
사용자의 쇼핑 요청을 분석하고 도움이 되는 응답을 생성해주세요.

사용자 요청: {request}

다음 형식으로 응답해주세요:
{{
  "analysis": "요청 분석 결과",
  "recommendations": ["추천사항1", "추천사항2", "추천사항3"],
  "next_steps": ["다음 단계1", "다음 단계2"],
  "helpful_tips": ["유용한 팁1", "유용한 팁2"]
}}
"""
        
        try:
            # Gemini API를 통해 응답 생성
            llm_response = await self.gemini_client.generate_text(
                prompt=prompt,
                config=GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1000
                )
            )
            
            # JSON 파싱 시도
            try:
                parsed_response = json.loads(llm_response)
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본 응답
                parsed_response = {
                    "analysis": "쇼핑 가격 비교 요청을 받았습니다.",
                    "recommendations": [
                        "여러 온라인 쇼핑몰에서 가격을 비교해보세요",
                        "할인 쿠폰이나 적립금을 확인해보세요",
                        "배송비와 반품 정책도 고려해보세요"
                    ],
                    "next_steps": [
                        "구체적인 상품명을 알려주시면 더 정확한 비교가 가능합니다",
                        "예산 범위를 설정해보세요"
                    ],
                    "helpful_tips": [
                        "가격 비교 사이트를 활용해보세요",
                        "리뷰와 평점도 함께 확인하는 것이 좋습니다"
                    ]
                }
            
            return {
                "success": True,
                "result": parsed_response,
                "llm_response": llm_response,
                "request_type": "shopping",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"쇼핑 요청 처리 실패: {e}")
            return {
                "success": False,
                "error": f"쇼핑 요청 처리 중 오류 발생: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_general_request(self, request: str, parsed_intent: ParsedIntent) -> Dict[str, Any]:
        """일반 요청 처리"""
        prompt = f"""
사용자의 요청에 대해 도움이 되는 응답을 생성해주세요.

사용자 요청: {request}

친절하고 유용한 정보를 제공해주세요.
"""
        
        try:
            llm_response = await self.gemini_client.generate_text(
                prompt=prompt,
                config=GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=800
                )
            )
            
            return {
                "success": True,
                "result": {
                    "response": llm_response,
                    "intent": parsed_intent.intent_type.value if parsed_intent else "unknown"
                },
                "llm_response": llm_response,
                "request_type": "general",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"일반 요청 처리 실패: {e}")
            return {
                "success": False,
                "error": f"요청 처리 중 오류 발생: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    @log_function_call
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """메시지 처리"""
        try:
            if message.message_type == "worker_registration":
                return await self._handle_worker_registration(message)
            elif message.message_type == "task_completion":
                return await self._handle_task_completion(message)
            elif message.message_type == "task_failure":
                return await self._handle_task_failure(message)
            elif message.message_type == "status_update":
                return await self._handle_status_update(message)
            elif message.message_type == "user_request":
                return await self._handle_user_request(message)
            else:
                self.logger.warning(f"알 수 없는 메시지 유형: {message.message_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"메시지 처리 실패: {e}")
            return None
    
    async def _handle_worker_registration(self, message: AgentMessage) -> Optional[AgentMessage]:
        """워커 등록 처리"""
        worker_info = message.content.get("worker_info", {})
        worker_id = message.sender_id
        
        self.worker_agents[worker_id] = {
            "id": worker_id,
            "name": worker_info.get("name", f"Worker-{worker_id}"),
            "skills": worker_info.get("skills", []),
            "status": "idle",
            "registered_at": datetime.now(),
            "last_seen": datetime.now()
        }
        
        self.logger.info(f"워커 등록: {worker_id}")
        
        # 등록 확인 응답
        return AgentMessage(
            id=f"reg_confirm_{worker_id}",
            sender_id=self.agent_id,
            receiver_id=worker_id,
            message_type="registration_confirmed",
            content={"status": "registered", "manager_id": self.agent_id},
            timestamp=datetime.now()
        )
    
    async def _handle_task_completion(self, message: AgentMessage) -> Optional[AgentMessage]:
        """작업 완료 처리"""
        task_result = message.content.get("task_result", {})
        task_id = task_result.get("task_id")
        worker_id = message.sender_id
        
        if task_id in self.task_assignments:
            # 작업 완료 기록
            self.logger.info(f"작업 완료 확인: {task_id} by {worker_id}")
            
            # 워커 상태 업데이트
            if worker_id in self.worker_agents:
                self.worker_agents[worker_id]["status"] = "idle"
                self.worker_agents[worker_id]["last_seen"] = datetime.now()
            
            # 프로젝트 진행 상황 업데이트
            await self._update_project_progress(task_id, "completed", task_result)
        
        return None
    
    async def _handle_task_failure(self, message: AgentMessage) -> Optional[AgentMessage]:
        """작업 실패 처리"""
        task_error = message.content.get("task_error", {})
        task_id = task_error.get("task_id")
        worker_id = message.sender_id
        error_message = task_error.get("error", "Unknown error")
        
        self.logger.error(f"작업 실패: {task_id} by {worker_id} - {error_message}")
        
        # 워커 상태 업데이트
        if worker_id in self.worker_agents:
            self.worker_agents[worker_id]["status"] = "idle"
            self.worker_agents[worker_id]["last_seen"] = datetime.now()
        
        # 재시도 또는 대체 방안 검토
        await self._handle_task_retry(task_id, error_message)
        
        return None
    
    async def _handle_status_update(self, message: AgentMessage) -> Optional[AgentMessage]:
        """상태 업데이트 처리"""
        status_info = message.content.get("status", {})
        worker_id = message.sender_id
        
        if worker_id in self.worker_agents:
            self.worker_agents[worker_id].update(status_info)
            self.worker_agents[worker_id]["last_seen"] = datetime.now()
        
        return None
    
    async def _handle_user_request(self, message: AgentMessage) -> Optional[AgentMessage]:
        """사용자 요청 처리"""
        user_input = message.content.get("user_input", "")
        
        # NLP 처리
        parsed_intent = await self.nlp_handler.parse_user_input(user_input)
        
        # 에이전트 작업 생성
        agent_tasks = await self.nlp_handler.generate_agent_tasks(parsed_intent)
        
        # 작업 큐에 추가
        for task in agent_tasks:
            await self.add_task(task)
        
        # 응답 생성
        response_text = await self.nlp_handler.generate_response(
            parsed_intent,
            [{"message": f"{len(agent_tasks)}개의 작업이 생성되어 처리 중입니다."}]
        )
        
        return AgentMessage(
            id=f"response_{message.id}",
            sender_id=self.agent_id,
            receiver_id=message.sender_id,
            message_type="user_response",
            content={"response": response_text},
            timestamp=datetime.now()
        )
    
    async def _update_project_progress(self, task_id: str, status: str, result: Dict[str, Any]):
        """프로젝트 진행 상황 업데이트"""
        # 해당 작업이 속한 프로젝트 찾기
        for project_id, project_info in self.active_projects.items():
            subtasks = project_info.get("subtasks", [])
            if any(subtask.task_id == task_id for subtask in subtasks):
                # 프로젝트 상태 업데이트
                if "completed_tasks" not in project_info:
                    project_info["completed_tasks"] = []
                
                project_info["completed_tasks"].append({
                    "task_id": task_id,
                    "status": status,
                    "result": result,
                    "completed_at": datetime.now()
                })
                
                # 프로젝트 완료 확인
                if len(project_info["completed_tasks"]) >= len(subtasks):
                    project_info["status"] = "completed"
                    project_info["end_time"] = datetime.now()
                    self.performance_metrics["completed_projects"] += 1
                    
                    self.logger.info(f"프로젝트 완료: {project_id}")
                
                break
    
    async def _handle_task_retry(self, task_id: str, error_message: str):
        """작업 재시도 처리"""
        # 재시도 로직 구현
        # 실제로는 더 복잡한 재시도 전략 필요
        self.logger.info(f"작업 재시도 검토: {task_id}")
    
    def get_manager_status(self) -> Dict[str, Any]:
        """매니저 상태 조회"""
        base_status = self.get_status_info()
        
        manager_specific = {
            "worker_agents": len(self.worker_agents),
            "active_projects": len(self.active_projects),
            "task_assignments": len(self.task_assignments),
            "performance_metrics": self.performance_metrics,
            "worker_status": {
                worker_id: info.get("status", "unknown")
                for worker_id, info in self.worker_agents.items()
            }
        }
        
        base_status.update(manager_specific)
        return base_status