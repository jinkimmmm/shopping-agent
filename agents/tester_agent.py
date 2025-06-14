"""테스터 에이전트 - 품질 보증 및 테스트"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

from .base_agent import (
    BaseAgent, AgentType, AgentStatus, AgentCapability,
    AgentTask, AgentMessage, TaskExecution, TaskStatus
)
from ai.gemini_client import GeminiClient, GenerationConfig
from ai.vector_db_handler import VectorDBHandler, Document, SearchQuery
from core.logger import log_function_call


class TestType(Enum):
    """테스트 유형"""
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USABILITY = "usability"
    INTEGRATION = "integration"
    REGRESSION = "regression"
    ACCEPTANCE = "acceptance"


class TestResult(Enum):
    """테스트 결과"""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


class TestCase:
    """테스트 케이스"""
    def __init__(
        self,
        test_id: str,
        name: str,
        description: str,
        test_type: TestType,
        expected_result: str,
        test_data: Dict[str, Any] = None,
        priority: int = 1
    ):
        self.test_id = test_id
        self.name = name
        self.description = description
        self.test_type = test_type
        self.expected_result = expected_result
        self.test_data = test_data or {}
        self.priority = priority
        self.created_at = datetime.now()


class TestExecution:
    """테스트 실행 결과"""
    def __init__(
        self,
        test_case: TestCase,
        result: TestResult,
        actual_result: str,
        execution_time: float,
        error_message: str = None,
        screenshots: List[str] = None
    ):
        self.test_case = test_case
        self.result = result
        self.actual_result = actual_result
        self.execution_time = execution_time
        self.error_message = error_message
        self.screenshots = screenshots or []
        self.executed_at = datetime.now()


class TesterAgent(BaseAgent):
    """테스터 에이전트 - 품질 보증 및 테스트 담당"""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        gemini_client: GeminiClient,
        vector_db_handler: VectorDBHandler
    ):
        """테스터 에이전트 초기화"""
        capabilities = [
            AgentCapability(
                name="test_case_generation",
                description="테스트 케이스 자동 생성",
                parameters={"test_types": [t.value for t in TestType]}
            ),
            AgentCapability(
                name="automated_testing",
                description="자동화된 테스트 실행",
                parameters={"parallel_execution": True, "retry_count": 3}
            ),
            AgentCapability(
                name="quality_assessment",
                description="품질 평가 및 분석",
                parameters={"quality_metrics": ["functionality", "performance", "security"]}
            ),
            AgentCapability(
                name="bug_detection",
                description="버그 탐지 및 분석",
                parameters={"detection_methods": ["static", "dynamic", "ai_based"]}
            ),
            AgentCapability(
                name="test_reporting",
                description="테스트 보고서 생성",
                parameters={"report_formats": ["html", "json", "pdf"]}
            )
        ]
        
        super().__init__(agent_id, AgentType.TESTER, name, gemini_client, capabilities)
        
        self.vector_db_handler = vector_db_handler
        
        # 테스트 관리
        self.test_suites: Dict[str, List[TestCase]] = {}
        self.test_executions: List[TestExecution] = []
        self.test_templates: Dict[str, Dict[str, Any]] = {}
        
        # 품질 메트릭
        self.quality_metrics = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_coverage": 0.0,
            "bug_detection_rate": 0.0,
            "false_positive_rate": 0.0,
            "average_execution_time": 0.0
        }
        
        # 테스트 설정
        self.test_config = {
            "timeout": 30,  # 초
            "retry_count": 3,
            "parallel_limit": 5,
            "quality_threshold": 0.8
        }
        
        # 매니저 정보
        self.manager_id: Optional[str] = None
        
        # 테스트 템플릿 초기화
        self._initialize_test_templates()
    
    def _initialize_test_templates(self):
        """테스트 템플릿 초기화"""
        self.test_templates = {
            "functional": {
                "description": "기능 테스트 템플릿",
                "test_steps": [
                    "입력 데이터 준비",
                    "기능 실행",
                    "결과 검증",
                    "정리 작업"
                ],
                "validation_criteria": [
                    "예상 결과와 일치",
                    "오류 없음",
                    "성능 기준 충족"
                ]
            },
            "performance": {
                "description": "성능 테스트 템플릿",
                "test_steps": [
                    "부하 시나리오 설정",
                    "성능 모니터링 시작",
                    "테스트 실행",
                    "성능 지표 수집",
                    "결과 분석"
                ],
                "validation_criteria": [
                    "응답 시간 기준 충족",
                    "처리량 기준 충족",
                    "리소스 사용량 적정"
                ]
            },
            "security": {
                "description": "보안 테스트 템플릿",
                "test_steps": [
                    "보안 취약점 스캔",
                    "인증/인가 테스트",
                    "데이터 보호 검증",
                    "보안 정책 준수 확인"
                ],
                "validation_criteria": [
                    "취약점 없음",
                    "인증 정상 작동",
                    "데이터 암호화 적용"
                ]
            }
        }
    
    @log_function_call
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """테스트 작업 처리"""
        try:
            self.logger.info(f"테스트 작업 시작: {task.task_id} ({task.task_type.value})")
            
            # 작업 유형별 처리
            if task.task_type.value == "quality_assurance":
                result = await self._process_quality_assurance(task)
            elif task.task_type.value == "test_generation":
                result = await self._process_test_generation(task)
            elif task.task_type.value == "test_execution":
                result = await self._process_test_execution(task)
            elif task.task_type.value == "bug_detection":
                result = await self._process_bug_detection(task)
            elif task.task_type.value == "test_reporting":
                result = await self._process_test_reporting(task)
            else:
                result = await self._process_general_testing(task)
            
            # 품질 메트릭 업데이트
            await self._update_quality_metrics(task, result)
            
            # 매니저에게 결과 보고
            await self._report_test_completion(task, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"테스트 작업 실패: {task.task_id} - {e}")
            
            await self._report_test_failure(task, str(e))
            
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _process_quality_assurance(self, task: AgentTask) -> Dict[str, Any]:
        """품질 보증 처리"""
        target_system = task.parameters.get("target_system", "")
        quality_criteria = task.parameters.get("quality_criteria", [])
        
        # 품질 평가 수행
        quality_assessment = await self._assess_system_quality(
            target_system, quality_criteria
        )
        
        # 개선 권장사항 생성
        recommendations = await self._generate_quality_recommendations(
            quality_assessment
        )
        
        return {
            "success": True,
            "task_id": task.task_id,
            "quality_assessment": quality_assessment,
            "recommendations": recommendations,
            "overall_score": quality_assessment.get("overall_score", 0.0)
        }
    
    async def _assess_system_quality(
        self, 
        target_system: str, 
        criteria: List[str]
    ) -> Dict[str, Any]:
        """시스템 품질 평가"""
        prompt = f"""
다음 시스템의 품질을 평가해주세요:

시스템: {target_system}
평가 기준: {', '.join(criteria)}

평가 항목:
1. 기능성 (Functionality)
2. 신뢰성 (Reliability)
3. 사용성 (Usability)
4. 효율성 (Efficiency)
5. 유지보수성 (Maintainability)
6. 이식성 (Portability)

각 항목을 1-10점으로 평가하고 상세한 분석을 제공해주세요.

응답 형식:
{{
  "functionality": {{"score": 8, "analysis": "분석 내용"}},
  "reliability": {{"score": 7, "analysis": "분석 내용"}},
  "usability": {{"score": 9, "analysis": "분석 내용"}},
  "efficiency": {{"score": 6, "analysis": "분석 내용"}},
  "maintainability": {{"score": 8, "analysis": "분석 내용"}},
  "portability": {{"score": 7, "analysis": "분석 내용"}},
  "overall_score": 7.5,
  "strengths": [],
  "weaknesses": [],
  "critical_issues": []
}}
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.2, max_output_tokens=1200)
            )
            
            return json.loads(response)
            
        except Exception as e:
            self.logger.error(f"품질 평가 실패: {e}")
            return {
                "overall_score": 0.0,
                "error": str(e)
            }
    
    async def _generate_quality_recommendations(
        self, 
        assessment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """품질 개선 권장사항 생성"""
        prompt = f"""
다음 품질 평가 결과를 바탕으로 개선 권장사항을 제시해주세요:

평가 결과: {json.dumps(assessment, ensure_ascii=False)}

권장사항 요구사항:
1. 구체적이고 실행 가능한 개선 방안
2. 우선순위 설정
3. 예상 효과 및 비용
4. 구현 일정 제안

응답 형식:
[
  {{
    "title": "개선사항 제목",
    "description": "상세 설명",
    "priority": "high|medium|low",
    "category": "기능성|신뢰성|사용성|효율성|유지보수성|이식성",
    "effort": "low|medium|high",
    "impact": "low|medium|high",
    "timeline": "예상 소요 시간",
    "implementation_steps": []
  }}
]
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.3, max_output_tokens=1000)
            )
            
            return json.loads(response)
            
        except Exception as e:
            self.logger.error(f"권장사항 생성 실패: {e}")
            return []
    
    async def _process_test_generation(self, task: AgentTask) -> Dict[str, Any]:
        """테스트 케이스 생성 처리"""
        requirements = task.parameters.get("requirements", "")
        test_types = task.parameters.get("test_types", ["functional"])
        coverage_target = task.parameters.get("coverage_target", 0.8)
        
        generated_tests = []
        
        for test_type in test_types:
            test_cases = await self._generate_test_cases(
                requirements, TestType(test_type), coverage_target
            )
            generated_tests.extend(test_cases)
        
        # 테스트 스위트에 추가
        suite_id = task.parameters.get("suite_id", f"suite_{task.task_id}")
        self.test_suites[suite_id] = generated_tests
        
        return {
            "success": True,
            "task_id": task.task_id,
            "suite_id": suite_id,
            "generated_tests": len(generated_tests),
            "test_cases": [
                {
                    "test_id": tc.test_id,
                    "name": tc.name,
                    "type": tc.test_type.value,
                    "priority": tc.priority
                }
                for tc in generated_tests
            ]
        }
    
    async def _generate_test_cases(
        self, 
        requirements: str, 
        test_type: TestType, 
        coverage_target: float
    ) -> List[TestCase]:
        """테스트 케이스 생성"""
        template = self.test_templates.get(test_type.value, {})
        
        prompt = f"""
다음 요구사항에 대한 {test_type.value} 테스트 케이스를 생성해주세요:

요구사항: {requirements}
테스트 유형: {test_type.value}
커버리지 목표: {coverage_target * 100}%

테스트 템플릿:
{json.dumps(template, ensure_ascii=False)}

생성 요구사항:
1. 포괄적인 테스트 커버리지
2. 경계값 및 예외 상황 포함
3. 우선순위 설정
4. 명확한 예상 결과

응답 형식:
[
  {{
    "test_id": "TC_001",
    "name": "테스트 케이스 이름",
    "description": "테스트 설명",
    "test_steps": [],
    "test_data": {{}},
    "expected_result": "예상 결과",
    "priority": 1
  }}
]
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.3, max_output_tokens=1500)
            )
            
            test_data = json.loads(response)
            
            test_cases = []
            for tc_data in test_data:
                test_case = TestCase(
                    test_id=tc_data["test_id"],
                    name=tc_data["name"],
                    description=tc_data["description"],
                    test_type=test_type,
                    expected_result=tc_data["expected_result"],
                    test_data=tc_data.get("test_data", {}),
                    priority=tc_data.get("priority", 1)
                )
                test_cases.append(test_case)
            
            return test_cases
            
        except Exception as e:
            self.logger.error(f"테스트 케이스 생성 실패: {e}")
            return []
    
    async def _process_test_execution(self, task: AgentTask) -> Dict[str, Any]:
        """테스트 실행 처리"""
        suite_id = task.parameters.get("suite_id", "")
        test_ids = task.parameters.get("test_ids", [])
        parallel = task.parameters.get("parallel", True)
        
        if suite_id and suite_id in self.test_suites:
            test_cases = self.test_suites[suite_id]
            if test_ids:
                test_cases = [tc for tc in test_cases if tc.test_id in test_ids]
        else:
            return {
                "success": False,
                "error": f"테스트 스위트를 찾을 수 없음: {suite_id}",
                "task_id": task.task_id
            }
        
        # 테스트 실행
        if parallel and len(test_cases) > 1:
            executions = await self._execute_tests_parallel(test_cases)
        else:
            executions = await self._execute_tests_sequential(test_cases)
        
        # 실행 결과 저장
        self.test_executions.extend(executions)
        
        # 결과 요약
        summary = self._summarize_test_results(executions)
        
        return {
            "success": True,
            "task_id": task.task_id,
            "suite_id": suite_id,
            "executed_tests": len(executions),
            "summary": summary,
            "executions": [
                {
                    "test_id": ex.test_case.test_id,
                    "result": ex.result.value,
                    "execution_time": ex.execution_time,
                    "error_message": ex.error_message
                }
                for ex in executions
            ]
        }
    
    async def _execute_tests_parallel(self, test_cases: List[TestCase]) -> List[TestExecution]:
        """병렬 테스트 실행"""
        semaphore = asyncio.Semaphore(self.test_config["parallel_limit"])
        
        async def execute_with_semaphore(test_case):
            async with semaphore:
                return await self._execute_single_test(test_case)
        
        tasks = [execute_with_semaphore(tc) for tc in test_cases]
        executions = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        valid_executions = []
        for i, result in enumerate(executions):
            if isinstance(result, Exception):
                # 예외 발생 시 실패 결과 생성
                execution = TestExecution(
                    test_case=test_cases[i],
                    result=TestResult.ERROR,
                    actual_result="",
                    execution_time=0.0,
                    error_message=str(result)
                )
                valid_executions.append(execution)
            else:
                valid_executions.append(result)
        
        return valid_executions
    
    async def _execute_tests_sequential(self, test_cases: List[TestCase]) -> List[TestExecution]:
        """순차 테스트 실행"""
        executions = []
        
        for test_case in test_cases:
            try:
                execution = await self._execute_single_test(test_case)
                executions.append(execution)
            except Exception as e:
                execution = TestExecution(
                    test_case=test_case,
                    result=TestResult.ERROR,
                    actual_result="",
                    execution_time=0.0,
                    error_message=str(e)
                )
                executions.append(execution)
        
        return executions
    
    async def _execute_single_test(self, test_case: TestCase) -> TestExecution:
        """단일 테스트 실행"""
        start_time = datetime.now()
        
        try:
            # 테스트 실행 시뮬레이션 (실제 구현에서는 실제 테스트 로직)
            actual_result = await self._simulate_test_execution(test_case)
            
            # 결과 검증
            test_result = await self._validate_test_result(
                test_case, actual_result
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TestExecution(
                test_case=test_case,
                result=test_result,
                actual_result=actual_result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TestExecution(
                test_case=test_case,
                result=TestResult.ERROR,
                actual_result="",
                execution_time=execution_time,
                error_message=str(e)
            )
    
    async def _simulate_test_execution(self, test_case: TestCase) -> str:
        """테스트 실행 시뮬레이션"""
        # 실제 구현에서는 실제 시스템과 상호작용
        prompt = f"""
다음 테스트 케이스를 실행하고 결과를 시뮬레이션해주세요:

테스트 케이스:
- ID: {test_case.test_id}
- 이름: {test_case.name}
- 설명: {test_case.description}
- 유형: {test_case.test_type.value}
- 테스트 데이터: {json.dumps(test_case.test_data, ensure_ascii=False)}
- 예상 결과: {test_case.expected_result}

실제 시스템에서 이 테스트를 실행했을 때의 결과를 시뮬레이션해주세요.
결과는 구체적이고 측정 가능한 형태로 제공해주세요.
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.4, max_output_tokens=500)
            )
            
            return response.strip()
            
        except Exception as e:
            raise Exception(f"테스트 실행 시뮬레이션 실패: {e}")
    
    async def _validate_test_result(
        self, 
        test_case: TestCase, 
        actual_result: str
    ) -> TestResult:
        """테스트 결과 검증"""
        prompt = f"""
다음 테스트 결과를 검증해주세요:

예상 결과: {test_case.expected_result}
실제 결과: {actual_result}

검증 기준:
1. 기능적 요구사항 충족
2. 성능 기준 만족
3. 오류 없음

결과를 다음 중 하나로 판정해주세요:
- PASS: 테스트 통과
- FAIL: 테스트 실패
- SKIP: 테스트 건너뜀
- ERROR: 실행 오류

판정 결과만 응답해주세요 (PASS, FAIL, SKIP, ERROR 중 하나).
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.1, max_output_tokens=50)
            )
            
            result_str = response.strip().upper()
            
            if result_str in ["PASS", "FAIL", "SKIP", "ERROR"]:
                return TestResult(result_str.lower())
            else:
                return TestResult.FAIL
                
        except Exception as e:
            self.logger.error(f"결과 검증 실패: {e}")
            return TestResult.ERROR
    
    def _summarize_test_results(self, executions: List[TestExecution]) -> Dict[str, Any]:
        """테스트 결과 요약"""
        total = len(executions)
        passed = sum(1 for ex in executions if ex.result == TestResult.PASS)
        failed = sum(1 for ex in executions if ex.result == TestResult.FAIL)
        errors = sum(1 for ex in executions if ex.result == TestResult.ERROR)
        skipped = sum(1 for ex in executions if ex.result == TestResult.SKIP)
        
        avg_execution_time = (
            sum(ex.execution_time for ex in executions) / total
            if total > 0 else 0.0
        )
        
        pass_rate = passed / total if total > 0 else 0.0
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "pass_rate": pass_rate,
            "average_execution_time": avg_execution_time,
            "status": "PASS" if pass_rate >= self.test_config["quality_threshold"] else "FAIL"
        }
    
    async def _process_bug_detection(self, task: AgentTask) -> Dict[str, Any]:
        """버그 탐지 처리"""
        target_code = task.parameters.get("target_code", "")
        detection_methods = task.parameters.get("detection_methods", ["static", "ai_based"])
        
        detected_bugs = []
        
        for method in detection_methods:
            if method == "static":
                bugs = await self._static_analysis(target_code)
            elif method == "dynamic":
                bugs = await self._dynamic_analysis(target_code)
            elif method == "ai_based":
                bugs = await self._ai_based_detection(target_code)
            else:
                continue
            
            detected_bugs.extend(bugs)
        
        # 중복 제거 및 우선순위 정렬
        unique_bugs = self._deduplicate_bugs(detected_bugs)
        prioritized_bugs = sorted(unique_bugs, key=lambda x: x.get("severity", 0), reverse=True)
        
        return {
            "success": True,
            "task_id": task.task_id,
            "detected_bugs": len(prioritized_bugs),
            "bugs": prioritized_bugs,
            "detection_methods": detection_methods
        }
    
    async def _static_analysis(self, code: str) -> List[Dict[str, Any]]:
        """정적 분석"""
        prompt = f"""
다음 코드에 대해 정적 분석을 수행하여 잠재적 버그를 탐지해주세요:

```
{code}
```

분석 항목:
1. 구문 오류
2. 타입 오류
3. 논리 오류
4. 성능 문제
5. 보안 취약점
6. 코드 스멜

응답 형식:
[
  {{
    "bug_id": "STATIC_001",
    "type": "syntax_error|type_error|logic_error|performance|security|code_smell",
    "severity": 1-10,
    "line_number": 10,
    "description": "버그 설명",
    "suggestion": "수정 제안",
    "detection_method": "static"
  }}
]
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.2, max_output_tokens=1000)
            )
            
            return json.loads(response)
            
        except Exception as e:
            self.logger.error(f"정적 분석 실패: {e}")
            return []
    
    async def _dynamic_analysis(self, code: str) -> List[Dict[str, Any]]:
        """동적 분석 (시뮬레이션)"""
        # 실제 구현에서는 코드 실행 및 모니터링
        prompt = f"""
다음 코드의 동적 실행을 시뮬레이션하여 런타임 버그를 탐지해주세요:

```
{code}
```

분석 항목:
1. 런타임 예외
2. 메모리 누수
3. 무한 루프
4. 데드락
5. 리소스 누수

응답 형식:
[
  {{
    "bug_id": "DYNAMIC_001",
    "type": "runtime_exception|memory_leak|infinite_loop|deadlock|resource_leak",
    "severity": 1-10,
    "description": "버그 설명",
    "reproduction_steps": [],
    "suggestion": "수정 제안",
    "detection_method": "dynamic"
  }}
]
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.3, max_output_tokens=800)
            )
            
            return json.loads(response)
            
        except Exception as e:
            self.logger.error(f"동적 분석 실패: {e}")
            return []
    
    async def _ai_based_detection(self, code: str) -> List[Dict[str, Any]]:
        """AI 기반 버그 탐지"""
        prompt = f"""
AI 기반 분석을 통해 다음 코드의 잠재적 문제점을 탐지해주세요:

```
{code}
```

분석 관점:
1. 패턴 기반 이상 탐지
2. 베스트 프랙티스 위반
3. 유지보수성 문제
4. 확장성 문제
5. 사용자 경험 영향

응답 형식:
[
  {{
    "bug_id": "AI_001",
    "type": "pattern_anomaly|best_practice_violation|maintainability|scalability|ux_impact",
    "severity": 1-10,
    "confidence": 0.8,
    "description": "문제점 설명",
    "impact": "영향도 분석",
    "suggestion": "개선 제안",
    "detection_method": "ai_based"
  }}
]
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.4, max_output_tokens=1000)
            )
            
            return json.loads(response)
            
        except Exception as e:
            self.logger.error(f"AI 기반 탐지 실패: {e}")
            return []
    
    def _deduplicate_bugs(self, bugs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """버그 중복 제거"""
        seen = set()
        unique_bugs = []
        
        for bug in bugs:
            # 버그 식별자 생성 (타입 + 설명의 해시)
            identifier = f"{bug.get('type', '')}_{hash(bug.get('description', ''))}"
            
            if identifier not in seen:
                seen.add(identifier)
                unique_bugs.append(bug)
        
        return unique_bugs
    
    async def _process_test_reporting(self, task: AgentTask) -> Dict[str, Any]:
        """테스트 보고서 생성 처리"""
        report_type = task.parameters.get("report_type", "summary")
        include_details = task.parameters.get("include_details", True)
        
        if report_type == "summary":
            report = await self._generate_summary_report(include_details)
        elif report_type == "detailed":
            report = await self._generate_detailed_report()
        elif report_type == "executive":
            report = await self._generate_executive_report()
        else:
            report = await self._generate_custom_report(task.parameters)
        
        return {
            "success": True,
            "task_id": task.task_id,
            "report_type": report_type,
            "report": report
        }
    
    async def _generate_summary_report(self, include_details: bool) -> Dict[str, Any]:
        """요약 보고서 생성"""
        recent_executions = self.test_executions[-100:]  # 최근 100개
        
        if not recent_executions:
            return {
                "message": "실행된 테스트가 없습니다.",
                "metrics": self.quality_metrics
            }
        
        summary = self._summarize_test_results(recent_executions)
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "quality_metrics": self.quality_metrics,
            "test_suites": {
                suite_id: len(tests)
                for suite_id, tests in self.test_suites.items()
            }
        }
        
        if include_details:
            report["recent_failures"] = [
                {
                    "test_id": ex.test_case.test_id,
                    "test_name": ex.test_case.name,
                    "error_message": ex.error_message,
                    "executed_at": ex.executed_at.isoformat()
                }
                for ex in recent_executions
                if ex.result in [TestResult.FAIL, TestResult.ERROR]
            ][-10:]  # 최근 10개 실패
        
        return report
    
    async def _generate_detailed_report(self) -> Dict[str, Any]:
        """상세 보고서 생성"""
        return {
            "generated_at": datetime.now().isoformat(),
            "test_suites": {
                suite_id: [
                    {
                        "test_id": tc.test_id,
                        "name": tc.name,
                        "description": tc.description,
                        "type": tc.test_type.value,
                        "priority": tc.priority,
                        "created_at": tc.created_at.isoformat()
                    }
                    for tc in tests
                ]
                for suite_id, tests in self.test_suites.items()
            },
            "test_executions": [
                {
                    "test_id": ex.test_case.test_id,
                    "result": ex.result.value,
                    "actual_result": ex.actual_result,
                    "execution_time": ex.execution_time,
                    "error_message": ex.error_message,
                    "executed_at": ex.executed_at.isoformat()
                }
                for ex in self.test_executions[-50:]  # 최근 50개
            ],
            "quality_metrics": self.quality_metrics
        }
    
    async def _generate_executive_report(self) -> Dict[str, Any]:
        """경영진 보고서 생성"""
        prompt = f"""
다음 테스트 메트릭을 바탕으로 경영진을 위한 요약 보고서를 작성해주세요:

품질 메트릭: {json.dumps(self.quality_metrics, ensure_ascii=False)}
테스트 스위트 수: {len(self.test_suites)}
총 실행 테스트: {len(self.test_executions)}

보고서 요구사항:
1. 핵심 성과 지표 (KPI)
2. 품질 트렌드 분석
3. 리스크 평가
4. 권장사항
5. 투자 대비 효과

응답 형식:
{{
  "executive_summary": "경영진 요약",
  "key_metrics": {{}},
  "quality_trends": [],
  "risk_assessment": {{}},
  "recommendations": [],
  "roi_analysis": {{}}
}}
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.3, max_output_tokens=1000)
            )
            
            return json.loads(response)
            
        except Exception as e:
            self.logger.error(f"경영진 보고서 생성 실패: {e}")
            return {
                "error": str(e),
                "fallback_metrics": self.quality_metrics
            }
    
    async def _generate_custom_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """사용자 정의 보고서 생성"""
        # 사용자 정의 보고서 로직
        return {
            "custom_report": "사용자 정의 보고서",
            "parameters": parameters,
            "generated_at": datetime.now().isoformat()
        }
    
    async def _process_general_testing(self, task: AgentTask) -> Dict[str, Any]:
        """일반 테스트 처리"""
        prompt = f"""
다음 테스트 작업을 수행해주세요:

작업 설명: {task.description}
작업 유형: {task.task_type.value}
매개변수: {json.dumps(task.parameters, ensure_ascii=False)}

테스트 관련 작업을 수행하고 결과를 JSON 형식으로 제공해주세요.
"""
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                GenerationConfig(temperature=0.4, max_output_tokens=1000)
            )
            
            try:
                result = json.loads(response)
            except:
                result = {"test_result": response}
            
            result["success"] = True
            result["task_id"] = task.task_id
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _update_quality_metrics(self, task: AgentTask, result: Dict[str, Any]):
        """품질 메트릭 업데이트"""
        if result.get("success", False):
            # 성공한 작업에 대한 메트릭 업데이트
            if "executed_tests" in result:
                self.quality_metrics["total_tests"] += result["executed_tests"]
                
                if "summary" in result:
                    summary = result["summary"]
                    self.quality_metrics["passed_tests"] += summary.get("passed", 0)
                    self.quality_metrics["failed_tests"] += summary.get("failed", 0)
                    
                    # 평균 실행 시간 업데이트
                    if "average_execution_time" in summary:
                        current_avg = self.quality_metrics["average_execution_time"]
                        new_avg = summary["average_execution_time"]
                        total_tests = self.quality_metrics["total_tests"]
                        
                        if total_tests > 0:
                            self.quality_metrics["average_execution_time"] = (
                                (current_avg * (total_tests - result["executed_tests"]) + 
                                 new_avg * result["executed_tests"]) / total_tests
                            )
            
            # 테스트 커버리지 업데이트 (간단한 추정)
            if self.quality_metrics["total_tests"] > 0:
                self.quality_metrics["test_coverage"] = min(
                    self.quality_metrics["passed_tests"] / 
                    self.quality_metrics["total_tests"], 1.0
                )
    
    async def _report_test_completion(self, task: AgentTask, result: Dict[str, Any]):
        """테스트 완료 보고"""
        if self.manager_id:
            message = AgentMessage(
                id=f"test_completion_{task.task_id}",
                sender_id=self.agent_id,
                receiver_id=self.manager_id,
                message_type="test_completion",
                content={
                    "test_result": result,
                    "quality_metrics": self.quality_metrics
                },
                timestamp=datetime.now()
            )
            
            await self.send_message(message)
    
    async def _report_test_failure(self, task: AgentTask, error_message: str):
        """테스트 실패 보고"""
        if self.manager_id:
            message = AgentMessage(
                id=f"test_failure_{task.task_id}",
                sender_id=self.agent_id,
                receiver_id=self.manager_id,
                message_type="test_failure",
                content={
                    "test_error": {
                        "task_id": task.task_id,
                        "error": error_message
                    }
                },
                timestamp=datetime.now()
            )
            
            await self.send_message(message)
    
    @log_function_call
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """메시지 처리"""
        try:
            if message.message_type == "test_request":
                return await self._handle_test_request(message)
            elif message.message_type == "quality_query":
                return await self._handle_quality_query(message)
            elif message.message_type == "manager_registration":
                return await self._handle_manager_registration(message)
            else:
                self.logger.warning(f"알 수 없는 메시지 유형: {message.message_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"메시지 처리 실패: {e}")
            return None
    
    async def _handle_test_request(self, message: AgentMessage) -> Optional[AgentMessage]:
        """테스트 요청 처리"""
        request_data = message.content.get("test_request", {})
        
        # 테스트 작업 생성
        task = AgentTask(
            task_id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            task_type=request_data.get("task_type", "test_execution"),
            description=request_data.get("description", "테스트 실행"),
            parameters=request_data.get("parameters", {}),
            priority=request_data.get("priority", 1)
        )
        
        # 작업 큐에 추가
        await self.add_task(task)
        
        return AgentMessage(
            id=f"test_ack_{task.task_id}",
            sender_id=self.agent_id,
            receiver_id=message.sender_id,
            message_type="test_acknowledged",
            content={"task_id": task.task_id, "status": "accepted"},
            timestamp=datetime.now()
        )
    
    async def _handle_quality_query(self, message: AgentMessage) -> Optional[AgentMessage]:
        """품질 쿼리 처리"""
        query_type = message.content.get("query_type", "metrics")
        
        if query_type == "metrics":
            response_content = self.quality_metrics
        elif query_type == "test_suites":
            response_content = {
                suite_id: len(tests)
                for suite_id, tests in self.test_suites.items()
            }
        elif query_type == "recent_results":
            response_content = [
                {
                    "test_id": ex.test_case.test_id,
                    "result": ex.result.value,
                    "execution_time": ex.execution_time
                }
                for ex in self.test_executions[-10:]
            ]
        else:
            response_content = {"error": f"알 수 없는 쿼리 유형: {query_type}"}
        
        return AgentMessage(
            id=f"quality_response_{message.id}",
            sender_id=self.agent_id,
            receiver_id=message.sender_id,
            message_type="quality_response",
            content=response_content,
            timestamp=datetime.now()
        )
    
    async def _handle_manager_registration(self, message: AgentMessage) -> Optional[AgentMessage]:
        """매니저 등록 처리"""
        self.manager_id = message.sender_id
        
        self.logger.info(f"매니저 등록됨: {self.manager_id}")
        
        return AgentMessage(
            id=f"tester_registration_ack",
            sender_id=self.agent_id,
            receiver_id=message.sender_id,
            message_type="tester_registration_confirmed",
            content={
                "tester_info": {
                    "name": self.name,
                    "capabilities": [cap.name for cap in self.capabilities],
                    "quality_metrics": self.quality_metrics
                }
            },
            timestamp=datetime.now()
        )
    
    def get_tester_status(self) -> Dict[str, Any]:
        """테스터 상태 조회"""
        base_status = self.get_status_info()
        
        tester_specific = {
            "manager_id": self.manager_id,
            "quality_metrics": self.quality_metrics,
            "test_suites": {
                suite_id: len(tests)
                for suite_id, tests in self.test_suites.items()
            },
            "recent_executions": len(self.test_executions),
            "test_config": self.test_config
        }
        
        base_status.update(tester_specific)
        return base_status