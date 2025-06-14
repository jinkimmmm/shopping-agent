"""워커 에이전트 - 실제 작업 수행"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base_agent import (
    BaseAgent, AgentType, AgentStatus, AgentCapability,
    AgentTask, AgentMessage, TaskExecution, TaskStatus
)
from ai.gemini_client import GeminiClient, GenerationConfig
from ai.vector_db_handler import VectorDBHandler, Document, SearchQuery
from core.logger import log_function_call


class WorkerAgent(BaseAgent):
    """워커 에이전트 - 실제 작업 수행 담당"""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        gemini_client: GeminiClient,
        vector_db_handler: VectorDBHandler,
        specialization: str = "general"
    ):
        """워커 에이전트 초기화"""
        # 전문 분야에 따른 능력 설정
        capabilities = self._get_capabilities_by_specialization(specialization)
        
        super().__init__(agent_id, AgentType.WORKER, name, gemini_client, capabilities)
        
        self.vector_db_handler = vector_db_handler
        self.specialization = specialization
        
        # 매니저 정보
        self.manager_id: Optional[str] = None
        self.registration_status = "unregistered"
        
        # 작업 실행 컨텍스트
        self.execution_context: Dict[str, Any] = {}
        self.knowledge_base: Dict[str, Any] = {}
        
        # 성능 메트릭
        self.specialization_metrics = {
            "tasks_by_type": {},
            "average_quality_score": 0.0,
            "expertise_level": 1.0,
            "learning_progress": 0.0
        }
    
    def _get_capabilities_by_specialization(self, specialization: str) -> List[AgentCapability]:
        """전문 분야별 능력 설정"""
        base_capabilities = [
            AgentCapability(
                name="text_processing",
                description="텍스트 처리 및 분석",
                parameters={"max_text_length": 10000, "languages": ["ko", "en"]}
            ),
            AgentCapability(
                name="information_retrieval",
                description="정보 검색 및 추출",
                parameters={"search_depth": 3, "relevance_threshold": 0.7}
            )
        ]
        
        if specialization == "document_processing":
            base_capabilities.extend([
                AgentCapability(
                    name="document_analysis",
                    description="문서 분석 및 요약",
                    parameters={"summary_ratio": 0.3, "key_points_extraction": True}
                ),
                AgentCapability(
                    name="content_extraction",
                    description="콘텐츠 추출 및 구조화",
                    parameters={"formats": ["pdf", "docx", "txt", "html"]}
                )
            ])
        
        elif specialization == "data_analysis":
            base_capabilities.extend([
                AgentCapability(
                    name="statistical_analysis",
                    description="통계 분석 및 인사이트 도출",
                    parameters={"analysis_types": ["descriptive", "correlation", "trend"]}
                ),
                AgentCapability(
                    name="data_visualization",
                    description="데이터 시각화",
                    parameters={"chart_types": ["bar", "line", "pie", "scatter"]}
                )
            ])
        
        elif specialization == "customer_service":
            base_capabilities.extend([
                AgentCapability(
                    name="customer_interaction",
                    description="고객 상호작용 및 지원",
                    parameters={"response_tone": "friendly", "escalation_rules": []}
                ),
                AgentCapability(
                    name="issue_resolution",
                    description="문제 해결 및 솔루션 제공",
                    parameters={"resolution_strategies": [], "knowledge_base_access": True}
                )
            ])
        
        elif specialization == "code_assistance":
            base_capabilities.extend([
                AgentCapability(
                    name="code_analysis",
                    description="코드 분석 및 리뷰",
                    parameters={"languages": ["python", "javascript", "java", "go"]}
                ),
                AgentCapability(
                    name="code_generation",
                    description="코드 생성 및 최적화",
                    parameters={"best_practices": True, "documentation": True}
                )
            ])
        
        return base_capabilities
    
    @log_function_call
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """작업 처리 - 전문 분야별 실행"""
        try:
            self.logger.info(
                f"작업 처리 시작: {task.task_id} ({task.task_type.value})",
                extra={"specialization": self.specialization}
            )
            
            # 작업 컨텍스트 설정
            await self._setup_task_context(task)
            
            # 전문 분야별 처리
            if self.specialization == "document_processing":
                result = await self._process_document_task(task)
            elif self.specialization == "data_analysis":
                result = await self._process_data_analysis_task(task)
            elif self.specialization == "customer_service":
                result = await self._process_customer_service_task(task)
            elif self.specialization == "code_assistance":
                result = await self._process_code_assistance_task(task)
            else:
                result = await self._process_general_task(task)
            
            # 결과 검증 및 품질 평가
            quality_score = await self._evaluate_result_quality(task, result)
            result["quality_score"] = quality_score
            
            # 학습 및 개선
            await self._update_learning_progress(task, result)
            
            # 매니저에게 완료 보고
            await self._report_task_completion(task, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"작업 처리 실패: {task.task_id} - {e}")
            
            # 매니저에게 실패 보고
            await self._report_task_failure(task, str(e))
            
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _setup_task_context(self, task: AgentTask):
        """작업 컨텍스트 설정"""
        self.execution_context = {
            "task_id": task.task_id,
            "start_time": datetime.now(),
            "parameters": task.parameters,
            "specialization": self.specialization
        }
        
        # 관련 지식 검색
        if task.description:
            relevant_knowledge = await self._search_relevant_knowledge(task.description)
            self.execution_context["relevant_knowledge"] = relevant_knowledge
    
    async def _search_relevant_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """관련 지식 검색"""
        try:
            search_query = SearchQuery(
                text=query,
                limit=5,
                threshold=0.6
            )
            
            search_results = await self.vector_db_handler.search_documents(search_query)
            
            return [
                {
                    "content": result.document.content,
                    "metadata": result.document.metadata,
                    "score": result.score
                }
                for result in search_results
            ]
            
        except Exception as e:
            self.logger.error(f"지식 검색 실패: {e}")
            return []
    
    async def _process_document_task(self, task: AgentTask) -> Dict[str, Any]:
        """문서 처리 작업"""
        document_content = task.parameters.get("document_content", "")
        processing_type = task.parameters.get("processing_type", "summary")
        
        if processing_type == "summary":
            return await self._summarize_document(document_content, task)
        elif processing_type == "analysis":
            return await self._analyze_document(document_content, task)
        elif processing_type == "extraction":
            return await self._extract_information(document_content, task)
        else:
            return await self._process_general_document(document_content, task)
    
    async def _summarize_document(self, content: str, task: AgentTask) -> Dict[str, Any]:
        """문서 요약"""
        summary_ratio = task.parameters.get("summary_ratio", 0.3)
        
        prompt = f"""
다음 문서를 요약해주세요. 요약 비율: {summary_ratio * 100}%

문서 내용:
{content}

요구사항:
1. 핵심 내용을 {summary_ratio * 100}% 길이로 요약
2. 주요 포인트를 불릿 포인트로 정리
3. 결론 또는 핵심 메시지 명시

응답 형식:
{{
  "summary": "요약 내용",
  "key_points": ["포인트1", "포인트2", ...],
  "conclusion": "결론",
  "word_count": 단어수
}}
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.3, max_output_tokens=1000)
            )
            
            result = json.loads(response)
            result["success"] = True
            result["task_id"] = task.task_id
            result["processing_type"] = "summary"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _analyze_document(self, content: str, task: AgentTask) -> Dict[str, Any]:
        """문서 분석"""
        analysis_type = task.parameters.get("analysis_type", "general")
        
        prompt = f"""
다음 문서를 분석해주세요. 분석 유형: {analysis_type}

문서 내용:
{content}

분석 요구사항:
1. 문서의 구조와 형식 분석
2. 주제와 키워드 추출
3. 감정 및 톤 분석
4. 정보의 신뢰성 평가
5. 개선 제안사항

응답 형식:
{{
  "structure_analysis": "구조 분석 결과",
  "topics": ["주제1", "주제2", ...],
  "keywords": ["키워드1", "키워드2", ...],
  "sentiment": "감정 분석 결과",
  "credibility_score": 0.8,
  "improvements": ["개선사항1", "개선사항2", ...]
}}
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.3, max_output_tokens=1200)
            )
            
            result = json.loads(response)
            result["success"] = True
            result["task_id"] = task.task_id
            result["processing_type"] = "analysis"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _extract_information(self, content: str, task: AgentTask) -> Dict[str, Any]:
        """정보 추출"""
        extraction_targets = task.parameters.get("extraction_targets", ["entities", "dates", "numbers"])
        
        prompt = f"""
다음 문서에서 정보를 추출해주세요.

문서 내용:
{content}

추출 대상: {', '.join(extraction_targets)}

응답 형식:
{{
  "entities": {{"persons": [], "organizations": [], "locations": []}},
  "dates": [],
  "numbers": [],
  "emails": [],
  "urls": [],
  "phone_numbers": [],
  "extracted_facts": []
}}
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.1, max_output_tokens=800)
            )
            
            result = json.loads(response)
            result["success"] = True
            result["task_id"] = task.task_id
            result["processing_type"] = "extraction"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _process_general_document(self, content: str, task: AgentTask) -> Dict[str, Any]:
        """일반 문서 처리"""
        prompt = f"""
다음 문서를 처리해주세요:

문서 내용:
{content}

작업 설명: {task.description}
매개변수: {json.dumps(task.parameters, ensure_ascii=False)}

적절한 처리를 수행하고 결과를 JSON 형식으로 제공해주세요.
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.4, max_output_tokens=1000)
            )
            
            # JSON 파싱 시도
            try:
                result = json.loads(response)
            except:
                result = {"processed_content": response}
            
            result["success"] = True
            result["task_id"] = task.task_id
            result["processing_type"] = "general"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _process_data_analysis_task(self, task: AgentTask) -> Dict[str, Any]:
        """데이터 분석 작업"""
        data = task.parameters.get("data", [])
        analysis_type = task.parameters.get("analysis_type", "descriptive")
        
        prompt = f"""
다음 데이터를 분석해주세요:

데이터: {json.dumps(data, ensure_ascii=False)}
분석 유형: {analysis_type}

분석 요구사항:
1. 기술 통계 (평균, 중앙값, 표준편차 등)
2. 데이터 분포 특성
3. 이상치 탐지
4. 트렌드 및 패턴 분석
5. 인사이트 및 권장사항

응답 형식:
{{
  "descriptive_stats": {{}},
  "distribution": {{}},
  "outliers": [],
  "trends": [],
  "insights": [],
  "recommendations": []
}}
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.2, max_output_tokens=1200)
            )
            
            result = json.loads(response)
            result["success"] = True
            result["task_id"] = task.task_id
            result["analysis_type"] = analysis_type
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _process_customer_service_task(self, task: AgentTask) -> Dict[str, Any]:
        """고객 서비스 작업"""
        customer_query = task.parameters.get("customer_query", "")
        customer_context = task.parameters.get("customer_context", {})
        
        prompt = f"""
고객 문의에 대해 친절하고 도움이 되는 응답을 생성해주세요.

고객 문의: {customer_query}
고객 컨텍스트: {json.dumps(customer_context, ensure_ascii=False)}

응답 요구사항:
1. 친근하고 전문적인 톤
2. 구체적이고 실용적인 해결책 제시
3. 추가 도움이 필요한 경우 안내
4. 고객 만족도 향상을 위한 배려

응답 형식:
{{
  "response": "고객 응답 내용",
  "solution_steps": ["단계1", "단계2", ...],
  "additional_resources": [],
  "escalation_needed": false,
  "satisfaction_score_prediction": 0.8
}}
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.5, max_output_tokens=1000)
            )
            
            result = json.loads(response)
            result["success"] = True
            result["task_id"] = task.task_id
            result["service_type"] = "customer_support"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _process_code_assistance_task(self, task: AgentTask) -> Dict[str, Any]:
        """코드 지원 작업"""
        code_content = task.parameters.get("code_content", "")
        assistance_type = task.parameters.get("assistance_type", "review")
        programming_language = task.parameters.get("language", "python")
        
        if assistance_type == "review":
            return await self._review_code(code_content, programming_language, task)
        elif assistance_type == "generation":
            return await self._generate_code(task)
        elif assistance_type == "debugging":
            return await self._debug_code(code_content, programming_language, task)
        else:
            return await self._general_code_assistance(code_content, task)
    
    async def _review_code(self, code: str, language: str, task: AgentTask) -> Dict[str, Any]:
        """코드 리뷰"""
        prompt = f"""
다음 {language} 코드를 리뷰해주세요:

```{language}
{code}
```

리뷰 기준:
1. 코드 품질 및 가독성
2. 성능 최적화 가능성
3. 보안 취약점
4. 베스트 프랙티스 준수
5. 버그 가능성

응답 형식:
{{
  "overall_score": 8.5,
  "quality_issues": [],
  "performance_suggestions": [],
  "security_concerns": [],
  "best_practice_violations": [],
  "potential_bugs": [],
  "improvement_suggestions": [],
  "positive_aspects": []
}}
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.2, max_output_tokens=1200)
            )
            
            result = json.loads(response)
            result["success"] = True
            result["task_id"] = task.task_id
            result["assistance_type"] = "review"
            result["language"] = language
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _generate_code(self, task: AgentTask) -> Dict[str, Any]:
        """코드 생성"""
        requirements = task.parameters.get("requirements", "")
        language = task.parameters.get("language", "python")
        
        prompt = f"""
다음 요구사항에 맞는 {language} 코드를 생성해주세요:

요구사항: {requirements}

코드 생성 기준:
1. 클린 코드 원칙 준수
2. 적절한 주석 포함
3. 에러 처리 포함
4. 테스트 가능한 구조
5. 문서화 포함

응답 형식:
{{
  "generated_code": "생성된 코드",
  "explanation": "코드 설명",
  "usage_example": "사용 예제",
  "dependencies": [],
  "test_suggestions": []
}}
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.3, max_output_tokens=1500)
            )
            
            result = json.loads(response)
            result["success"] = True
            result["task_id"] = task.task_id
            result["assistance_type"] = "generation"
            result["language"] = language
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _debug_code(self, code: str, language: str, task: AgentTask) -> Dict[str, Any]:
        """코드 디버깅"""
        error_message = task.parameters.get("error_message", "")
        
        prompt = f"""
다음 {language} 코드의 오류를 분석하고 수정 방안을 제시해주세요:

```{language}
{code}
```

오류 메시지: {error_message}

분석 및 수정 요구사항:
1. 오류 원인 분석
2. 수정된 코드 제공
3. 예방 방법 제시
4. 관련 베스트 프랙티스

응답 형식:
{{
  "error_analysis": "오류 분석",
  "root_cause": "근본 원인",
  "fixed_code": "수정된 코드",
  "explanation": "수정 설명",
  "prevention_tips": [],
  "related_best_practices": []
}}
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.2, max_output_tokens=1200)
            )
            
            result = json.loads(response)
            result["success"] = True
            result["task_id"] = task.task_id
            result["assistance_type"] = "debugging"
            result["language"] = language
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _general_code_assistance(self, code: str, task: AgentTask) -> Dict[str, Any]:
        """일반 코드 지원"""
        prompt = f"""
다음 코드 지원 요청을 처리해주세요:

코드: {code}
작업 설명: {task.description}
매개변수: {json.dumps(task.parameters, ensure_ascii=False)}

적절한 코드 지원을 제공하고 결과를 JSON 형식으로 제공해주세요.
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.3, max_output_tokens=1000)
            )
            
            try:
                result = json.loads(response)
            except:
                result = {"assistance_content": response}
            
            result["success"] = True
            result["task_id"] = task.task_id
            result["assistance_type"] = "general"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _process_general_task(self, task: AgentTask) -> Dict[str, Any]:
        """일반 작업 처리"""
        prompt = f"""
다음 작업을 수행해주세요:

작업 설명: {task.description}
작업 유형: {task.task_type.value}
매개변수: {json.dumps(task.parameters, ensure_ascii=False)}

관련 지식:
{json.dumps(self.execution_context.get('relevant_knowledge', []), ensure_ascii=False)}

작업을 수행하고 결과를 JSON 형식으로 제공해주세요.
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.4, max_output_tokens=1000)
            )
            
            try:
                result = json.loads(response)
            except:
                result = {"task_result": response}
            
            result["success"] = True
            result["task_id"] = task.task_id
            result["task_type"] = task.task_type.value
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _evaluate_result_quality(self, task: AgentTask, result: Dict[str, Any]) -> float:
        """결과 품질 평가"""
        # 기본 품질 점수
        base_score = 0.7
        
        # 성공 여부
        if result.get("success", False):
            base_score += 0.2
        
        # 결과 완성도
        if "error" not in result:
            base_score += 0.1
        
        # 전문 분야 일치도
        if self.specialization in str(result):
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    async def _update_learning_progress(self, task: AgentTask, result: Dict[str, Any]):
        """학습 진행 상황 업데이트"""
        task_type = task.task_type.value
        
        # 작업 유형별 통계 업데이트
        if task_type not in self.specialization_metrics["tasks_by_type"]:
            self.specialization_metrics["tasks_by_type"][task_type] = 0
        self.specialization_metrics["tasks_by_type"][task_type] += 1
        
        # 품질 점수 평균 업데이트
        quality_score = result.get("quality_score", 0.7)
        current_avg = self.specialization_metrics["average_quality_score"]
        total_tasks = sum(self.specialization_metrics["tasks_by_type"].values())
        
        self.specialization_metrics["average_quality_score"] = (
            (current_avg * (total_tasks - 1) + quality_score) / total_tasks
        )
        
        # 전문성 레벨 업데이트
        if quality_score > 0.8:
            self.specialization_metrics["expertise_level"] += 0.01
        
        self.specialization_metrics["expertise_level"] = min(
            self.specialization_metrics["expertise_level"], 10.0
        )
    
    async def _report_task_completion(self, task: AgentTask, result: Dict[str, Any]):
        """작업 완료 보고"""
        if self.manager_id:
            message = AgentMessage(
                id=f"completion_{task.task_id}",
                sender_id=self.agent_id,
                receiver_id=self.manager_id,
                message_type="task_completion",
                content={
                    "task_result": result,
                    "execution_time": (
                        datetime.now() - self.execution_context["start_time"]
                    ).total_seconds(),
                    "specialization": self.specialization
                },
                timestamp=datetime.now()
            )
            
            await self.send_message(message)
    
    async def _report_task_failure(self, task: AgentTask, error_message: str):
        """작업 실패 보고"""
        if self.manager_id:
            message = AgentMessage(
                id=f"failure_{task.task_id}",
                sender_id=self.agent_id,
                receiver_id=self.manager_id,
                message_type="task_failure",
                content={
                    "task_error": {
                        "task_id": task.task_id,
                        "error": error_message,
                        "specialization": self.specialization
                    }
                },
                timestamp=datetime.now()
            )
            
            await self.send_message(message)
    
    @log_function_call
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """메시지 처리"""
        try:
            if message.message_type == "task_assignment":
                return await self._handle_task_assignment(message)
            elif message.message_type == "registration_confirmed":
                return await self._handle_registration_confirmation(message)
            elif message.message_type == "manager_query":
                return await self._handle_manager_query(message)
            else:
                self.logger.warning(f"알 수 없는 메시지 유형: {message.message_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"메시지 처리 실패: {e}")
            return None
    
    async def _handle_task_assignment(self, message: AgentMessage) -> Optional[AgentMessage]:
        """작업 할당 처리"""
        task_data = message.content.get("task", {})
        
        # AgentTask 객체 생성
        task = AgentTask(
            task_id=task_data.get("task_id", ""),
            task_type=task_data.get("task_type", "general_chat"),
            description=task_data.get("description", ""),
            parameters=task_data.get("parameters", {}),
            priority=task_data.get("priority", 1),
            dependencies=task_data.get("dependencies", [])
        )
        
        # 작업 큐에 추가
        await self.add_task(task)
        
        self.logger.info(f"작업 할당 받음: {task.task_id}")
        
        # 확인 응답
        return AgentMessage(
            id=f"ack_{task.task_id}",
            sender_id=self.agent_id,
            receiver_id=message.sender_id,
            message_type="task_acknowledged",
            content={"task_id": task.task_id, "status": "accepted"},
            timestamp=datetime.now()
        )
    
    async def _handle_registration_confirmation(self, message: AgentMessage) -> Optional[AgentMessage]:
        """등록 확인 처리"""
        self.manager_id = message.content.get("manager_id")
        self.registration_status = "registered"
        
        self.logger.info(f"매니저 등록 확인: {self.manager_id}")
        
        return None
    
    async def _handle_manager_query(self, message: AgentMessage) -> Optional[AgentMessage]:
        """매니저 쿼리 처리"""
        query_type = message.content.get("query_type", "status")
        
        if query_type == "status":
            response_content = self.get_worker_status()
        elif query_type == "metrics":
            response_content = self.specialization_metrics
        else:
            response_content = {"error": f"알 수 없는 쿼리 유형: {query_type}"}
        
        return AgentMessage(
            id=f"query_response_{message.id}",
            sender_id=self.agent_id,
            receiver_id=message.sender_id,
            message_type="query_response",
            content=response_content,
            timestamp=datetime.now()
        )
    
    @log_function_call
    async def register_with_manager(self, manager_id: str) -> bool:
        """매니저에게 등록"""
        try:
            message = AgentMessage(
                id=f"registration_{self.agent_id}",
                sender_id=self.agent_id,
                receiver_id=manager_id,
                message_type="worker_registration",
                content={
                    "worker_info": {
                        "name": self.name,
                        "specialization": self.specialization,
                        "skills": [cap.name for cap in self.capabilities],
                        "capabilities": [cap.name for cap in self.capabilities]
                    }
                },
                timestamp=datetime.now()
            )
            
            await self.send_message(message)
            
            self.logger.info(f"매니저 등록 요청 전송: {manager_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"매니저 등록 실패: {e}")
            return False
    
    def get_worker_status(self) -> Dict[str, Any]:
        """워커 상태 조회"""
        base_status = self.get_status_info()
        
        worker_specific = {
            "specialization": self.specialization,
            "manager_id": self.manager_id,
            "registration_status": self.registration_status,
            "specialization_metrics": self.specialization_metrics,
            "execution_context": {
                k: v for k, v in self.execution_context.items()
                if k != "relevant_knowledge"  # 너무 큰 데이터 제외
            }
        }
        
        base_status.update(worker_specific)
        return base_status