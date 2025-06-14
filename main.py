#!/usr/bin/env python3
"""쇼핑 에이전트 메인 애플리케이션"""

import asyncio
import signal
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime
import argparse
import json

from core.config import get_config, load_config
from core.logger import setup_logging, get_logger
from ai.gemini_client import GeminiClient  # core -> ai로 변경
from ai.vector_db_handler import VectorDBHandler  # core.vector_db -> ai.vector_db_handler로 변경
from agents.manager_agent import ManagerAgent
from agents.worker_agent import WorkerAgent
from agents.tester_agent import TesterAgent
from ai.agent_nlp_handler import AgentNLPHandler
from workflow.workflow_engine import WorkflowEngine
# from workflow.workflow_scheduler import WorkflowScheduler  # 파일이 없으므로 주석 처리
from workflow.workflow_monitor import WorkflowMonitor
from tools.tool_manager import get_tool_manager
# from communication.message_bus import get_message_bus  # 폴더가 없으므로 주석 처리
# from communication.protocol import MessageType  # 폴더가 없으므로 주석 처리


class ShoppingAgentApp:
    """쇼핑 에이전트 메인 애플리케이션"""
    
    def __init__(self, config_path: Optional[str] = None):
        """애플리케이션 초기화"""
        # 설정 로드
        if config_path:
            load_config(config_path)
        
        self.config = get_config()
        
        # 로깅 설정
        setup_logging()
        self.logger = get_logger(__name__)
        
        # 상태
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        # 핵심 컴포넌트
        self.gemini_client: Optional[GeminiClient] = None
        self.vector_db: Optional[VectorDBHandler] = None
        self.message_bus: Optional[Any] = None
        self.tool_manager: Optional[Any] = None
        
        # 에이전트들
        self.manager_agent: Optional[ManagerAgent] = None
        self.worker_agents: List[WorkerAgent] = []
        self.tester_agent: Optional[TesterAgent] = None
        
        # 워크플로우 시스템
        self.workflow_engine: Optional[WorkflowEngine] = None
        self.workflow_scheduler: Optional[Any] = None
        self.workflow_monitor: Optional[WorkflowMonitor] = None
        
        # 시그널 핸들러 설정
        self._setup_signal_handlers()
        
        self.logger.info("쇼핑 에이전트 애플리케이션이 초기화되었습니다")
    
    def _setup_signal_handlers(self):
        """시그널 핸들러 설정"""
        def signal_handler(signum, frame):
            self.logger.info(f"시그널 {signum} 수신, 종료 프로세스 시작")
            if self.is_running:
                self.is_running = False
                self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def initialize(self):
        """애플리케이션 초기화"""
        try:
            self.logger.info("애플리케이션 초기화 시작")
            
            # 1. 핵심 서비스 초기화
            await self._initialize_core_services()
            
            # 2. 에이전트 초기화
            await self._initialize_agents()
            
            # 3. 워크플로우 시스템 초기화
            await self._initialize_workflow_system()
            
            # 4. 도구 관리자 초기화
            await self._initialize_tool_manager()
            
            # 5. 메시지 버스 시작
            await self._start_message_bus()
            
            self.logger.info("애플리케이션 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"애플리케이션 초기화 실패: {str(e)}")
            raise
    
    async def _initialize_core_services(self):
        """핵심 서비스 초기화"""
        self.logger.info("핵심 서비스 초기화 중...")
        
        # Gemini 클라이언트 초기화
        self.gemini_client = GeminiClient()
        
        # 벡터 데이터베이스 초기화
        self.vector_db = VectorDBHandler(
            gemini_client=self.gemini_client,
            db_type=self.config.vector_db_type
        )
        
        # 메시지 버스 초기화 (주석 처리)
        # self.message_bus = get_message_bus()
        
        self.logger.info("핵심 서비스 초기화 완료")
    
    async def _initialize_agents(self):
        """에이전트 초기화"""
        self.logger.info("에이전트 초기화 중...")
        
        if not self.gemini_client:
            raise ValueError("GeminiClient가 초기화되지 않았습니다")
        
        # 매니저 에이전트 초기화
        nlp_handler = AgentNLPHandler(self.gemini_client)
        self.manager_agent = ManagerAgent(
            agent_id="manager_001",
            name="Manager Agent",
            gemini_client=self.gemini_client,
            nlp_handler=nlp_handler
        )
        
        # 워커 에이전트들 초기화
        worker_configs = []
        
        # 기본 워커 에이전트 설정이 없으면 생성
        if not worker_configs:
            worker_configs = [
                {"specialization": "document_processing", "agent_id": "worker_doc_001"},
                {"specialization": "data_analysis", "agent_id": "worker_data_001"},
                {"specialization": "customer_service", "agent_id": "worker_cs_001"},
                {"specialization": "code_assistance", "agent_id": "worker_code_001"},
                {"specialization": "general", "agent_id": "worker_general_001"}
            ]
        
        if not self.vector_db:
            raise ValueError("VectorDBHandler가 초기화되지 않았습니다")
            
        for worker_config in worker_configs:
            worker = WorkerAgent(
                agent_id=worker_config.get("agent_id", f"worker_{len(self.worker_agents)+1:03d}"),
                name=f"Worker {worker_config.get('specialization', 'general')}",
                gemini_client=self.gemini_client,
                vector_db_handler=self.vector_db,
                specialization=worker_config.get("specialization", "general")
            )
            self.worker_agents.append(worker)
        
        # 테스터 에이전트 초기화
        self.tester_agent = TesterAgent(
            agent_id="tester_001",
            name="Tester Agent",
            gemini_client=self.gemini_client,
            vector_db_handler=self.vector_db
        )
        
        self.logger.info(f"에이전트 초기화 완료: 매니저 1개, 워커 {len(self.worker_agents)}개, 테스터 1개")
    
    async def _initialize_workflow_system(self):
        """워크플로우 시스템 초기화"""
        self.logger.info("워크플로우 시스템 초기화 중...")
        
        # 워크플로우 엔진 초기화
        self.workflow_engine = WorkflowEngine()
        
        # 에이전트들을 워크플로우 엔진에 등록
        if self.manager_agent:
            self.workflow_engine.register_agent(self.manager_agent)
        for worker in self.worker_agents:
            self.workflow_engine.register_agent(worker)
        if self.tester_agent:
            self.workflow_engine.register_agent(self.tester_agent)
        
        # 워크플로우 스케줄러 초기화 (주석 처리)
        # scheduler_config = {}
        # self.workflow_scheduler = WorkflowScheduler(scheduler_config)
        
        # 워크플로우 모니터 초기화
        self.workflow_monitor = WorkflowMonitor()
        
        # 모니터링 시작
        await self.workflow_monitor.start_monitoring()
        
        self.logger.info("워크플로우 시스템 초기화 완료")
    
    async def _initialize_tool_manager(self):
        """도구 관리자 초기화"""
        self.logger.info("도구 관리자 초기화 중...")
        
        self.tool_manager = get_tool_manager()
        
        # 자동 정리 작업 시작
        self.tool_manager.start_auto_cleanup()
        
        self.logger.info("도구 관리자 초기화 완료")
    
    async def _start_message_bus(self):
        """메시지 버스 시작"""
        self.logger.info("메시지 버스 시작 중...")
        
        # 메시지 버스가 없으므로 주석 처리
        # 에이전트들을 메시지 버스에 등록
        # await self.message_bus.register_agent(self.manager_agent.agent_id, self.manager_agent)
        
        # for worker in self.worker_agents:
        #     await self.message_bus.register_agent(worker.agent_id, worker)
        
        # await self.message_bus.register_agent(self.tester_agent.agent_id, self.tester_agent)
        
        # 워커 에이전트들을 매니저에 등록
        if self.manager_agent:
            for worker in self.worker_agents:
                await worker.register_with_manager(self.manager_agent.agent_id)
        
        self.logger.info("메시지 버스 시작 완료")
    
    async def run(self):
        """애플리케이션 실행"""
        try:
            self.logger.info("쇼핑 에이전트 애플리케이션 시작")
            
            # 초기화
            await self.initialize()
            
            self.is_running = True
            
            # 시작 메시지 출력
            self._print_startup_info()
            
            # 메인 루프
            await self._main_loop()
            
        except KeyboardInterrupt:
            self.logger.info("사용자에 의해 중단됨")
        except Exception as e:
            self.logger.error(f"애플리케이션 실행 중 오류: {str(e)}")
            raise
        finally:
            await self.shutdown()
    
    async def _main_loop(self):
        """메인 실행 루프"""
        self.logger.info("메인 루프 시작")
        
        try:
            # 종료 이벤트 대기
            await self.shutdown_event.wait()
        except asyncio.CancelledError:
            self.logger.info("메인 루프가 취소되었습니다")
    
    def _print_startup_info(self):
        """시작 정보 출력"""
        print("\n" + "="*60)
        print("🛒 쇼핑 에이전트 시스템")
        print("="*60)
        print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"매니저 에이전트: {self.manager_agent.agent_id if self.manager_agent else 'None'}")
        print(f"워커 에이전트: {len(self.worker_agents)}개")
        print(f"테스터 에이전트: {self.tester_agent.agent_id if self.tester_agent else 'None'}")
        print(f"등록된 도구: {len(self.tool_manager.tools) if self.tool_manager else 0}개")
        print("\n시스템이 준비되었습니다. 작업을 시작할 수 있습니다.")
        print("종료하려면 Ctrl+C를 누르세요.")
        print("="*60 + "\n")
    
    async def process_user_request(self, request: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """사용자 요청 처리"""
        try:
            self.logger.info(f"사용자 요청 처리 시작: {request[:100]}...")
            
            # 매니저 에이전트에게 요청 전달
            if self.manager_agent and hasattr(self.manager_agent, 'process_request'):
                response = await self.manager_agent.process_request(request, context or {})
                
                # 응답 포맷팅 및 출력
                self._display_response(response)
                
            else:
                response = {
                    "success": True,
                    "result": f"Processing request: {request}",
                    "timestamp": datetime.now().isoformat()
                }
            
            self.logger.info("사용자 요청 처리 완료")
            return response
            
        except Exception as e:
            self.logger.error(f"사용자 요청 처리 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _display_response(self, response: Dict[str, Any]):
        """응답을 보기 좋게 출력"""
        print("\n" + "="*60)
        print("🤖 AI 에이전트 응답")
        print("="*60)
        
        if response.get("success"):
            result = response.get("result", {})
            request_type = response.get("request_type", "general")
            
            if request_type == "shopping" and isinstance(result, dict):
                # 쇼핑 요청 응답 포맷
                print(f"\n📊 분석 결과: {result.get('analysis', 'N/A')}")
                
                recommendations = result.get('recommendations', [])
                if recommendations:
                    print("\n💡 추천사항:")
                    for i, rec in enumerate(recommendations, 1):
                        print(f"  {i}. {rec}")
                
                next_steps = result.get('next_steps', [])
                if next_steps:
                    print("\n📋 다음 단계:")
                    for i, step in enumerate(next_steps, 1):
                        print(f"  {i}. {step}")
                
                helpful_tips = result.get('helpful_tips', [])
                if helpful_tips:
                    print("\n💎 유용한 팁:")
                    for i, tip in enumerate(helpful_tips, 1):
                        print(f"  {i}. {tip}")
                        
            elif isinstance(result, dict) and "response" in result:
                # 일반 요청 응답 포맷
                print(f"\n📝 응답: {result['response']}")
                if "intent" in result:
                    print(f"\n🎯 감지된 의도: {result['intent']}")
            else:
                # 기본 포맷
                print(f"\n📝 응답: {result}")
            
            # LLM 원본 응답 (디버깅용)
            llm_response = response.get("llm_response")
            if llm_response and len(llm_response) > 100:
                print(f"\n🔍 LLM 원본 응답 (처음 200자): {llm_response[:200]}...")
            elif llm_response:
                print(f"\n🔍 LLM 원본 응답: {llm_response}")
                
        else:
            print(f"\n❌ 오류 발생: {response.get('error', 'Unknown error')}")
        
        print(f"\n⏰ 처리 시간: {response.get('timestamp', 'N/A')}")
        print("="*60 + "\n")
    
    async def create_workflow(self, workflow_def: Dict[str, Any]) -> str:
        """워크플로우 생성"""
        if not self.workflow_engine:
            raise RuntimeError("워크플로우 엔진이 초기화되지 않았습니다")
        try:
            from workflow.workflow_models import Workflow, WorkflowStep, WorkflowVariable, StepType
            import uuid
            
            # 워크플로우 ID 생성 (없는 경우)
            workflow_id = workflow_def.get("workflow_id", str(uuid.uuid4()))
            
            # Steps 변환
            steps = []
            for step_data in workflow_def.get("steps", []):
                step = WorkflowStep(
                    step_id=step_data.get("id", ""),
                    name=step_data.get("name", ""),
                    step_type=StepType(step_data.get("type", "task")),
                    agent_type=step_data.get("agent_id", ""),
                    dependencies=step_data.get("dependencies", []),
                    parameters=step_data.get("config", {})
                )
                steps.append(step)
            
            # Variables 변환
            variables = []
            for var_name, var_value in workflow_def.get("variables", {}).items():
                variable = WorkflowVariable(
                    name=var_name,
                    value=var_value
                )
                variables.append(variable)
            
            # Dict에서 Workflow 객체 생성
            from workflow.workflow_models import WorkflowStatus
            workflow = Workflow(
                workflow_id=workflow_id,
                name=workflow_def.get("name", ""),
                description=workflow_def.get("description", ""),
                steps=steps,
                variables=variables,
                status=WorkflowStatus.ACTIVE  # 워크플로우를 활성 상태로 설정
            )
            
            success = await self.workflow_engine.create_workflow(workflow)
            if success:
                self.logger.info(f"워크플로우 생성됨: {workflow.workflow_id}")
                return workflow.workflow_id
            else:
                raise RuntimeError("워크플로우 생성 실패")
        except Exception as e:
            self.logger.error(f"워크플로우 생성 실패: {str(e)}")
            raise
    
    async def start_workflow(self, workflow_id: str, input_data: Optional[Dict[str, Any]] = None) -> str:
        """워크플로우 시작"""
        if not self.workflow_engine:
            raise RuntimeError("워크플로우 엔진이 초기화되지 않았습니다")
        try:
            execution_id = await self.workflow_engine.start_workflow(workflow_id, input_data or {})
            if execution_id is None:
                raise RuntimeError("워크플로우 시작 실패: execution_id가 None입니다")
            self.logger.info(f"워크플로우 시작됨: {workflow_id} -> {execution_id}")
            return execution_id
        except Exception as e:
            self.logger.error(f"워크플로우 시작 실패: {str(e)}")
            raise
    
    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 조회"""
        return {
            "is_running": self.is_running,
            "timestamp": datetime.now().isoformat(),
            "agents": {
                "manager": {
                    "id": self.manager_agent.agent_id if self.manager_agent else "none",
                    "status": "active" if self.is_running else "inactive"
                },
                "workers": [
                    {
                        "id": worker.agent_id,
                        "specialization": worker.specialization,
                        "status": "active" if self.is_running else "inactive"
                    }
                    for worker in self.worker_agents
                ],
                "tester": {
                    "id": self.tester_agent.agent_id if self.tester_agent else "none",
                    "status": "active" if self.is_running else "inactive"
                }
            },
            "workflow": {
                "engine_status": "active" if self.workflow_engine else "inactive",
                "active_workflows": len(getattr(self.workflow_engine, 'executions', {})) if self.workflow_engine else 0,
                "total_workflows": len(getattr(self.workflow_engine, 'workflows', {})) if self.workflow_engine else 0
            },
            "tools": self.tool_manager.get_statistics() if self.tool_manager else {},
            "message_bus": {
                "registered_agents": 0,
                "message_queue_size": 0
            }
        }
    
    async def shutdown(self):
        """애플리케이션 종료"""
        if not self.is_running:
            return
        
        self.logger.info("애플리케이션 종료 시작")
        self.is_running = False
        
        try:
            # 1. 워크플로우 시스템 종료
            if self.workflow_monitor:
                await self.workflow_monitor.stop_monitoring()
            
            if self.workflow_scheduler:
                await self.workflow_scheduler.stop()
            
            if self.workflow_engine:
                await self.workflow_engine.shutdown()
            
            # 2. 도구 관리자 종료
            if self.tool_manager:
                await self.tool_manager.shutdown()
            
            # 3. 메시지 버스 종료 (주석 처리)
            # if self.message_bus:
            #     await self.message_bus.shutdown()
            
            # 4. 벡터 데이터베이스 종료
            if self.vector_db:
                await self.vector_db.close()
            
            # 5. 종료 이벤트 설정
            self.shutdown_event.set()
            
            self.logger.info("애플리케이션 종료 완료")
            
        except Exception as e:
            self.logger.error(f"애플리케이션 종료 중 오류: {str(e)}")


def create_sample_workflow() -> Dict[str, Any]:
    """샘플 워크플로우 생성"""
    return {
        "name": "상품 정보 수집 및 분석",
        "description": "온라인 쇼핑몰에서 상품 정보를 수집하고 분석하는 워크플로우",
        "steps": [
            {
                "id": "collect_data",
                "name": "상품 데이터 수집",
                "type": "task",
                "agent_id": "worker_doc_001",
                "config": {
                    "task_type": "web_scraping",
                    "target_urls": ["https://example-shop.com/products"]
                }
            },
            {
                "id": "analyze_data",
                "name": "데이터 분석",
                "type": "task",
                "agent_id": "worker_data_001",
                "dependencies": ["collect_data"],
                "config": {
                    "task_type": "data_analysis",
                    "analysis_type": "price_trend"
                }
            },
            {
                "id": "generate_report",
                "name": "보고서 생성",
                "type": "task",
                "agent_id": "worker_doc_001",
                "dependencies": ["analyze_data"],
                "config": {
                    "task_type": "document_generation",
                    "template": "product_analysis_report"
                }
            }
        ],
        "variables": {
            "target_category": "electronics",
            "max_products": 100
        }
    }


async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="쇼핑 에이전트 시스템")
    parser.add_argument("--config", "-c", help="설정 파일 경로")
    parser.add_argument("--demo", action="store_true", help="데모 모드로 실행")
    parser.add_argument("--request", "-r", help="처리할 사용자 요청")
    parser.add_argument("--workflow", "-w", help="실행할 워크플로우 파일")
    
    args = parser.parse_args()
    
    # 애플리케이션 생성
    app = ShoppingAgentApp(args.config)
    
    try:
        if args.demo:
            # 데모 모드
            await run_demo(app)
        elif args.request:
            # 단일 요청 처리
            await run_single_request(app, args.request)
        elif args.workflow:
            # 워크플로우 실행
            await run_workflow_file(app, args.workflow)
        else:
            # 일반 실행
            await app.run()
    
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        sys.exit(1)


async def run_demo(app: ShoppingAgentApp):
    """데모 모드 실행"""
    print("\n🎯 데모 모드로 실행 중...")
    
    # 초기화
    await app.initialize()
    
    # 샘플 워크플로우 생성 및 실행
    workflow_def = create_sample_workflow()
    workflow_id = await app.create_workflow(workflow_def)
    
    print(f"\n📋 샘플 워크플로우 생성됨: {workflow_id}")
    
    # 워크플로우 시작
    execution_id = await app.start_workflow(workflow_id, {
        "target_category": "스마트폰",
        "max_products": 50
    })
    
    print(f"🚀 워크플로우 실행 시작: {execution_id}")
    
    # 잠시 대기 후 상태 확인
    await asyncio.sleep(5)
    
    status = app.get_system_status()
    print(f"\n📊 시스템 상태:")
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    print("\n✅ 데모 완료")


async def run_single_request(app: ShoppingAgentApp, request: str):
    """단일 요청 처리"""
    print(f"\n🎯 요청 처리 중: {request}")
    
    # 초기화
    await app.initialize()
    
    # 요청 처리
    response = await app.process_user_request(request)
    
    print(f"\n📋 처리 결과:")
    print(json.dumps(response, indent=2, ensure_ascii=False))


async def run_workflow_file(app: ShoppingAgentApp, workflow_file: str):
    """워크플로우 파일 실행"""
    print(f"\n🎯 워크플로우 파일 실행: {workflow_file}")
    
    try:
        with open(workflow_file, 'r', encoding='utf-8') as f:
            workflow_def = json.load(f)
        
        # 초기화
        await app.initialize()
        
        # 워크플로우 생성 및 실행
        workflow_id = await app.create_workflow(workflow_def)
        execution_id = await app.start_workflow(workflow_id)
        
        print(f"\n🚀 워크플로우 실행 시작: {execution_id}")
        
        # 완료 대기 (간단한 폴링)
        while True:
            await asyncio.sleep(2)
            # 실제로는 워크플로우 상태를 확인해야 함
            break
        
        print("\n✅ 워크플로우 실행 완료")
        
    except FileNotFoundError:
        print(f"❌ 워크플로우 파일을 찾을 수 없습니다: {workflow_file}")
    except json.JSONDecodeError:
        print(f"❌ 워크플로우 파일 형식이 올바르지 않습니다: {workflow_file}")
    except Exception as e:
        print(f"❌ 워크플로우 실행 실패: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())