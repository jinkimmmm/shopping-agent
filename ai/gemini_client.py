"""Google Gemini API 클라이언트"""

import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
import json

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core import retry

from core.config import settings
from core.logger import LoggerMixin, log_function_call


@dataclass
class ChatMessage:
    """채팅 메시지 데이터 클래스"""
    role: str  # 'user', 'model', 'system'
    content: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class GenerationConfig:
    """생성 설정 데이터 클래스"""
    temperature: float = 0.7
    top_p: float = 0.8
    top_k: int = 40
    max_output_tokens: int = 2048
    stop_sequences: Optional[List[str]] = None


class GeminiClient(LoggerMixin):
    """Google Gemini API 클라이언트"""
    
    def __init__(self):
        """클라이언트 초기화"""
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model
        self.model = None
        self.chat_session = None
        
        # API 키 설정
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self._initialize_model()
        else:
            self.logger.warning("Gemini API 키가 설정되지 않았습니다")
    
    def _initialize_model(self):
        """모델 초기화"""
        try:
            # 안전 설정
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            # 모델 초기화
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                safety_settings=safety_settings
            )
            
            self.logger.info(f"Gemini 모델 초기화 완료: {self.model_name}")
            
        except Exception as e:
            self.logger.error(f"Gemini 모델 초기화 실패: {e}")
            raise
    
    @log_function_call
    async def generate_text(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None
    ) -> str:
        """텍스트 생성"""
        if not self.model:
            raise ValueError("Gemini 모델이 초기화되지 않았습니다")
        
        if config is None:
            config = GenerationConfig()
        
        try:
            # 생성 설정
            generation_config = genai.types.GenerationConfig(
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                max_output_tokens=config.max_output_tokens,
                stop_sequences=config.stop_sequences
            )
            
            # 비동기 텍스트 생성
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=generation_config
            )
            
            # 응답 검증
            if not response.text:
                self.logger.warning("Gemini 응답이 비어있습니다")
                return ""
            
            self.logger.info(
                "텍스트 생성 완료",
                extra={
                    "prompt_length": len(prompt),
                    "response_length": len(response.text),
                    "model": self.model_name
                }
            )
            
            return response.text
            
        except Exception as e:
            self.logger.error(f"텍스트 생성 실패: {e}")
            raise
    
    @log_function_call
    async def generate_stream(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None
    ) -> AsyncGenerator[str, None]:
        """스트리밍 텍스트 생성"""
        if not self.model:
            raise ValueError("Gemini 모델이 초기화되지 않았습니다")
        
        if config is None:
            config = GenerationConfig()
        
        try:
            # 생성 설정
            generation_config = genai.types.GenerationConfig(
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                max_output_tokens=config.max_output_tokens,
                stop_sequences=config.stop_sequences
            )
            
            # 스트리밍 생성
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=generation_config,
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
            
            self.logger.info("스트리밍 텍스트 생성 완료")
            
        except Exception as e:
            self.logger.error(f"스트리밍 텍스트 생성 실패: {e}")
            raise
    
    @log_function_call
    async def start_chat(
        self,
        history: Optional[List[ChatMessage]] = None
    ) -> None:
        """채팅 세션 시작"""
        if not self.model:
            raise ValueError("Gemini 모델이 초기화되지 않았습니다")
        
        try:
            # 히스토리 변환
            chat_history = []
            if history:
                for msg in history:
                    if msg.role in ['user', 'model']:
                        chat_history.append({
                            'role': msg.role,
                            'parts': [msg.content]
                        })
            
            # 채팅 세션 시작
            self.chat_session = self.model.start_chat(history=chat_history)
            
            self.logger.info(
                "채팅 세션 시작",
                extra={"history_length": len(chat_history)}
            )
            
        except Exception as e:
            self.logger.error(f"채팅 세션 시작 실패: {e}")
            raise
    
    @log_function_call
    async def send_message(
        self,
        message: str,
        config: Optional[GenerationConfig] = None
    ) -> str:
        """채팅 메시지 전송"""
        if not self.chat_session:
            await self.start_chat()
        
        if config is None:
            config = GenerationConfig()
        
        try:
            # 생성 설정
            generation_config = genai.types.GenerationConfig(
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                max_output_tokens=config.max_output_tokens,
                stop_sequences=config.stop_sequences
            )
            
            # 메시지 전송
            response = await asyncio.to_thread(
                self.chat_session.send_message,
                message,
                generation_config=generation_config
            )
            
            self.logger.info(
                "채팅 메시지 전송 완료",
                extra={
                    "message_length": len(message),
                    "response_length": len(response.text) if response.text else 0
                }
            )
            
            return response.text if response.text else ""
            
        except Exception as e:
            self.logger.error(f"채팅 메시지 전송 실패: {e}")
            raise
    
    @log_function_call
    async def analyze_content(
        self,
        content: str,
        analysis_type: str = "general"
    ) -> Dict[str, Any]:
        """콘텐츠 분석"""
        analysis_prompts = {
            "general": f"다음 내용을 분석하고 주요 포인트를 요약해주세요:\n\n{content}",
            "sentiment": f"다음 텍스트의 감정을 분석해주세요 (긍정/부정/중립):\n\n{content}",
            "intent": f"다음 사용자 요청의 의도를 파악해주세요:\n\n{content}",
            "summary": f"다음 내용을 간결하게 요약해주세요:\n\n{content}"
        }
        
        prompt = analysis_prompts.get(analysis_type, analysis_prompts["general"])
        
        try:
            result = await self.generate_text(prompt)
            
            return {
                "analysis_type": analysis_type,
                "content_length": len(content),
                "result": result,
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            self.logger.error(f"콘텐츠 분석 실패: {e}")
            raise
    
    def get_chat_history(self) -> List[ChatMessage]:
        """채팅 히스토리 반환"""
        if not self.chat_session:
            return []
        
        history = []
        for msg in self.chat_session.history:
            history.append(ChatMessage(
                role=msg.role,
                content=msg.parts[0].text if msg.parts else ""
            ))
        
        return history
    
    def clear_chat_history(self):
        """채팅 히스토리 초기화"""
        self.chat_session = None
        self.logger.info("채팅 히스토리 초기화 완료")