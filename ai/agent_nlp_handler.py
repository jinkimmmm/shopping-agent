"""에이전트 자연어 처리 핸들러"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .gemini_client import GeminiClient, GenerationConfig
from core.logger import LoggerMixin, log_function_call


class IntentType(Enum):
    """의도 유형 열거형"""
    QUESTION = "question"  # 질문
    COMMAND = "command"   # 명령
    REQUEST = "request"   # 요청
    GREETING = "greeting" # 인사
    UNKNOWN = "unknown"   # 알 수 없음


class TaskType(Enum):
    """작업 유형 열거형"""
    DOCUMENT_SUMMARY = "document_summary"     # 문서 요약
    DATA_ANALYSIS = "data_analysis"           # 데이터 분석
    WORKFLOW_AUTOMATION = "workflow_automation" # 워크플로우 자동화
    CUSTOMER_SUPPORT = "customer_support"     # 고객 지원
    CODE_ASSISTANCE = "code_assistance"       # 코드 지원
    GENERAL_CHAT = "general_chat"             # 일반 대화


@dataclass
class ParsedIntent:
    """파싱된 의도 데이터 클래스"""
    intent_type: IntentType
    task_type: TaskType
    entities: Dict[str, Any]
    confidence: float
    original_text: str
    processed_text: str


@dataclass
class AgentTask:
    """에이전트 작업 데이터 클래스"""
    task_id: str
    task_type: TaskType
    description: str
    parameters: Dict[str, Any]
    priority: int = 1
    dependencies: List[str] = None


class AgentNLPHandler(LoggerMixin):
    """에이전트 자연어 처리 핸들러"""
    
    def __init__(self, gemini_client: GeminiClient):
        """핸들러 초기화"""
        self.gemini_client = gemini_client
        self.intent_patterns = self._load_intent_patterns()
        self.entity_extractors = self._load_entity_extractors()
    
    def _load_intent_patterns(self) -> Dict[str, List[str]]:
        """의도 패턴 로드"""
        return {
            "question": [
                r"\b(무엇|어떻게|왜|언제|어디서|누가)\b",
                r"\?$",
                r"\b(알려주|설명해|가르쳐)\b"
            ],
            "command": [
                r"\b(실행해|시작해|중지해|종료해)\b",
                r"\b(만들어|생성해|삭제해)\b",
                r"\b(분석해|요약해|처리해)\b"
            ],
            "request": [
                r"\b(부탁|요청|도움)\b",
                r"\b(해주세요|해줘|부탁해)\b",
                r"\b(필요해|원해|하고싶어)\b"
            ],
            "greeting": [
                r"\b(안녕|반가워|처음|시작)\b",
                r"\b(hello|hi|hey)\b",
                r"\b(좋은|감사)\b"
            ]
        }
    
    def _load_entity_extractors(self) -> Dict[str, str]:
        """엔티티 추출기 로드"""
        return {
            "file_path": r"([\w\-_\.]+\.(txt|pdf|docx|xlsx|csv|json|py|js|html|md))",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "url": r"https?://[\w\-._~:/?#[\]@!$&'()*+,;=%]+",
            "date": r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
            "number": r"\b\d+(?:\.\d+)?\b",
            "korean_name": r"[가-힣]{2,4}(?:\s+[가-힣]{1,3})*"
        }
    
    @log_function_call
    async def parse_user_input(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ParsedIntent:
        """사용자 입력 파싱"""
        try:
            # 텍스트 전처리
            processed_text = self._preprocess_text(user_input)
            
            # 의도 분류
            intent_type = await self._classify_intent(processed_text)
            
            # 작업 유형 분류
            task_type = await self._classify_task_type(processed_text, context)
            
            # 엔티티 추출
            entities = self._extract_entities(processed_text)
            
            # 신뢰도 계산
            confidence = await self._calculate_confidence(
                processed_text, intent_type, task_type
            )
            
            parsed_intent = ParsedIntent(
                intent_type=intent_type,
                task_type=task_type,
                entities=entities,
                confidence=confidence,
                original_text=user_input,
                processed_text=processed_text
            )
            
            self.logger.info(
                "사용자 입력 파싱 완료",
                extra={
                    "intent_type": intent_type.value,
                    "task_type": task_type.value,
                    "confidence": confidence,
                    "entities_count": len(entities)
                }
            )
            
            return parsed_intent
            
        except Exception as e:
            self.logger.error(f"사용자 입력 파싱 실패: {e}")
            # 기본값 반환
            return ParsedIntent(
                intent_type=IntentType.UNKNOWN,
                task_type=TaskType.GENERAL_CHAT,
                entities={},
                confidence=0.0,
                original_text=user_input,
                processed_text=user_input
            )
    
    def _preprocess_text(self, text: str) -> str:
        """텍스트 전처리"""
        # 소문자 변환
        text = text.lower()
        
        # 특수 문자 정규화
        text = re.sub(r'[^\w\s가-힣.,!?]', ' ', text)
        
        # 연속된 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        # 앞뒤 공백 제거
        text = text.strip()
        
        return text
    
    async def _classify_intent(self, text: str) -> IntentType:
        """의도 분류"""
        # 패턴 기반 분류
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return IntentType(intent)
        
        # LLM 기반 분류
        try:
            prompt = f"""
다음 텍스트의 의도를 분류해주세요.
가능한 의도: question, command, request, greeting, unknown

텍스트: "{text}"

응답 형식: {{"intent": "분류결과"}}
"""
            
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.1, max_output_tokens=100)
            )
            
            # JSON 파싱
            result = json.loads(response)
            intent_str = result.get("intent", "unknown")
            
            return IntentType(intent_str)
            
        except Exception as e:
            self.logger.warning(f"LLM 의도 분류 실패: {e}")
            return IntentType.UNKNOWN
    
    async def _classify_task_type(self, text: str, context: Optional[Dict[str, Any]]) -> TaskType:
        """작업 유형 분류"""
        # 키워드 기반 분류
        task_keywords = {
            TaskType.DOCUMENT_SUMMARY: ["요약", "정리", "summary", "문서"],
            TaskType.DATA_ANALYSIS: ["분석", "데이터", "통계", "차트", "그래프"],
            TaskType.WORKFLOW_AUTOMATION: ["자동화", "워크플로우", "프로세스", "작업"],
            TaskType.CUSTOMER_SUPPORT: ["고객", "지원", "문의", "도움", "서비스"],
            TaskType.CODE_ASSISTANCE: ["코드", "프로그래밍", "개발", "버그", "함수"]
        }
        
        for task_type, keywords in task_keywords.items():
            if any(keyword in text for keyword in keywords):
                return task_type
        
        # LLM 기반 분류
        try:
            context_str = json.dumps(context) if context else "없음"
            prompt = f"""
다음 텍스트의 작업 유형을 분류해주세요.
가능한 작업 유형: document_summary, data_analysis, workflow_automation, customer_support, code_assistance, general_chat

텍스트: "{text}"
컨텍스트: {context_str}

응답 형식: {{"task_type": "분류결과"}}
"""
            
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.1, max_output_tokens=100)
            )
            
            # JSON 파싱
            result = json.loads(response)
            task_type_str = result.get("task_type", "general_chat")
            
            return TaskType(task_type_str)
            
        except Exception as e:
            self.logger.warning(f"LLM 작업 유형 분류 실패: {e}")
            return TaskType.GENERAL_CHAT
    
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """엔티티 추출"""
        entities = {}
        
        for entity_type, pattern in self.entity_extractors.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches
        
        return entities
    
    async def _calculate_confidence(self, text: str, intent_type: IntentType, task_type: TaskType) -> float:
        """신뢰도 계산"""
        # 기본 신뢰도
        base_confidence = 0.5
        
        # 패턴 매칭 보너스
        pattern_bonus = 0.0
        if intent_type != IntentType.UNKNOWN:
            pattern_bonus += 0.2
        
        # 텍스트 길이 보너스
        length_bonus = min(len(text.split()) * 0.05, 0.2)
        
        # 특수 키워드 보너스
        keyword_bonus = 0.0
        if any(word in text for word in ["분석", "요약", "도움", "질문"]):
            keyword_bonus = 0.1
        
        confidence = min(base_confidence + pattern_bonus + length_bonus + keyword_bonus, 1.0)
        
        return round(confidence, 2)
    
    @log_function_call
    async def generate_agent_tasks(
        self,
        parsed_intent: ParsedIntent,
        context: Optional[Dict[str, Any]] = None
    ) -> List[AgentTask]:
        """에이전트 작업 생성"""
        try:
            context_str = json.dumps(context) if context else "없음"
            
            prompt = f"""
다음 사용자 요청을 기반으로 에이전트가 수행할 작업들을 생성해주세요.

사용자 요청:
- 원본 텍스트: "{parsed_intent.original_text}"
- 의도: {parsed_intent.intent_type.value}
- 작업 유형: {parsed_intent.task_type.value}
- 엔티티: {json.dumps(parsed_intent.entities, ensure_ascii=False)}
- 컨텍스트: {context_str}

작업을 단계별로 분해하여 JSON 배열로 응답해주세요.
각 작업은 다음 형식을 따라야 합니다:
{{
  "task_id": "고유_작업_ID",
  "task_type": "작업_유형",
  "description": "작업_설명",
  "parameters": {{"매개변수": "값"}},
  "priority": 1,
  "dependencies": ["의존_작업_ID"]
}}

응답 형식: {{"tasks": [작업_배열]}}
"""
            
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.3, max_output_tokens=1000)
            )
            
            # JSON 파싱
            result = json.loads(response)
            tasks_data = result.get("tasks", [])
            
            # AgentTask 객체 생성
            tasks = []
            for task_data in tasks_data:
                task = AgentTask(
                    task_id=task_data.get("task_id", f"task_{len(tasks)}"),
                    task_type=TaskType(task_data.get("task_type", "general_chat")),
                    description=task_data.get("description", ""),
                    parameters=task_data.get("parameters", {}),
                    priority=task_data.get("priority", 1),
                    dependencies=task_data.get("dependencies", [])
                )
                tasks.append(task)
            
            self.logger.info(
                "에이전트 작업 생성 완료",
                extra={"tasks_count": len(tasks)}
            )
            
            return tasks
            
        except Exception as e:
            self.logger.error(f"에이전트 작업 생성 실패: {e}")
            # 기본 작업 반환
            return [AgentTask(
                task_id="default_task",
                task_type=parsed_intent.task_type,
                description=f"사용자 요청 처리: {parsed_intent.original_text}",
                parameters={"user_input": parsed_intent.original_text}
            )]
    
    @log_function_call
    async def generate_response(
        self,
        parsed_intent: ParsedIntent,
        task_results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """응답 생성"""
        try:
            context_str = json.dumps(context) if context else "없음"
            results_str = json.dumps(task_results, ensure_ascii=False)
            
            prompt = f"""
다음 정보를 바탕으로 사용자에게 적절한 응답을 생성해주세요.

사용자 요청:
- 원본 텍스트: "{parsed_intent.original_text}"
- 의도: {parsed_intent.intent_type.value}
- 작업 유형: {parsed_intent.task_type.value}

작업 결과:
{results_str}

컨텍스트: {context_str}

응답 요구사항:
1. 친근하고 도움이 되는 톤으로 작성
2. 작업 결과를 명확하게 요약
3. 필요시 추가 도움 제안
4. 한국어로 응답
"""
            
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.7, max_output_tokens=1000)
            )
            
            self.logger.info("응답 생성 완료")
            
            return response
            
        except Exception as e:
            self.logger.error(f"응답 생성 실패: {e}")
            return "죄송합니다. 응답을 생성하는 중에 오류가 발생했습니다. 다시 시도해 주세요."