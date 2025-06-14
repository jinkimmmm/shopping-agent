"""API 클라이언트 도구 - REST API 호출 및 응답 처리"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin, urlparse
from datetime import datetime

from .base_tool import BaseTool, ToolResult, ToolType, ToolConfig
from core.logger import log_function_call


class APIClientTool(BaseTool):
    """API 클라이언트 도구"""
    
    def __init__(self, config: ToolConfig = None):
        """API 클라이언트 초기화"""
        super().__init__("api_client", ToolType.API_CLIENT, config)
        
        # 기본 헤더
        self.default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ShoppingAgent-APIClient/1.0"
        }
        
        # 인증 정보
        self.auth_tokens = {}
        
        # API 호출 통계
        self.api_calls_made = 0
        self.total_response_time = 0
        self.error_count = 0
        
        # 레이트 리미팅
        self.rate_limits = {}
        self.last_call_times = {}
    
    def get_description(self) -> str:
        """도구 설명 반환"""
        return "REST API를 호출하고 응답을 처리하는 도구입니다. GET, POST, PUT, DELETE 등의 HTTP 메서드를 지원합니다."
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        """매개변수 스키마 반환"""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "API 엔드포인트 URL"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                    "default": "GET",
                    "description": "HTTP 메서드"
                },
                "headers": {
                    "type": "object",
                    "description": "추가 HTTP 헤더"
                },
                "params": {
                    "type": "object",
                    "description": "URL 쿼리 매개변수"
                },
                "data": {
                    "type": "object",
                    "description": "요청 본문 데이터 (JSON)"
                },
                "json_data": {
                    "type": "object",
                    "description": "JSON 형태의 요청 데이터"
                },
                "form_data": {
                    "type": "object",
                    "description": "폼 데이터"
                },
                "auth": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["bearer", "basic", "api_key", "oauth2"]
                        },
                        "token": {
                            "type": "string",
                            "description": "인증 토큰"
                        },
                        "username": {
                            "type": "string",
                            "description": "사용자명 (Basic Auth)"
                        },
                        "password": {
                            "type": "string",
                            "description": "비밀번호 (Basic Auth)"
                        },
                        "api_key": {
                            "type": "string",
                            "description": "API 키"
                        },
                        "key_header": {
                            "type": "string",
                            "default": "X-API-Key",
                            "description": "API 키 헤더명"
                        }
                    },
                    "description": "인증 정보"
                },
                "timeout": {
                    "type": "integer",
                    "default": 30,
                    "description": "요청 타임아웃 (초)"
                },
                "retry_count": {
                    "type": "integer",
                    "default": 3,
                    "description": "재시도 횟수"
                },
                "retry_delay": {
                    "type": "number",
                    "default": 1.0,
                    "description": "재시도 간격 (초)"
                },
                "follow_redirects": {
                    "type": "boolean",
                    "default": True,
                    "description": "리다이렉트 따라가기 여부"
                },
                "verify_ssl": {
                    "type": "boolean",
                    "default": True,
                    "description": "SSL 인증서 검증 여부"
                },
                "response_format": {
                    "type": "string",
                    "enum": ["json", "text", "binary", "auto"],
                    "default": "auto",
                    "description": "응답 형식"
                }
            },
            "required": ["url"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """API 호출 실행"""
        url = kwargs.get("url")
        method = kwargs.get("method", "GET").upper()
        headers = kwargs.get("headers", {})
        params = kwargs.get("params", {})
        data = kwargs.get("data")
        json_data = kwargs.get("json_data")
        form_data = kwargs.get("form_data")
        auth = kwargs.get("auth")
        timeout = kwargs.get("timeout", 30)
        retry_count = kwargs.get("retry_count", 3)
        retry_delay = kwargs.get("retry_delay", 1.0)
        follow_redirects = kwargs.get("follow_redirects", True)
        verify_ssl = kwargs.get("verify_ssl", True)
        response_format = kwargs.get("response_format", "auto")
        
        try:
            # URL 유효성 검사
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return ToolResult.error_result("유효하지 않은 URL입니다")
            
            # 레이트 리미팅 확인
            if not await self._check_rate_limit(url):
                return ToolResult.error_result("레이트 리미트에 도달했습니다")
            
            # 요청 헤더 준비
            request_headers = {**self.default_headers, **headers}
            
            # 인증 처리
            if auth:
                self._apply_authentication(request_headers, auth)
            
            # 재시도 로직으로 API 호출
            start_time = datetime.now()
            response_data = None
            last_error = None
            
            for attempt in range(retry_count + 1):
                try:
                    response_data = await self._make_request(
                        url, method, request_headers, params, 
                        data, json_data, form_data, timeout, 
                        follow_redirects, verify_ssl
                    )
                    
                    if response_data["success"]:
                        break
                    else:
                        last_error = response_data["error"]
                        if attempt < retry_count:
                            await asyncio.sleep(retry_delay * (2 ** attempt))  # 지수 백오프
                        
                except Exception as e:
                    last_error = str(e)
                    if attempt < retry_count:
                        await asyncio.sleep(retry_delay * (2 ** attempt))
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            # 통계 업데이트
            self.api_calls_made += 1
            self.total_response_time += response_time
            
            if not response_data or not response_data["success"]:
                self.error_count += 1
                return ToolResult.error_result(f"API 호출 실패: {last_error}")
            
            # 응답 데이터 처리
            processed_response = await self._process_response(
                response_data, response_format
            )
            
            result_data = {
                "url": url,
                "method": method,
                "status_code": response_data["status_code"],
                "headers": response_data["headers"],
                "response": processed_response,
                "response_time": response_time,
                "attempts": attempt + 1,
                "timestamp": end_time.isoformat()
            }
            
            return ToolResult.success_result(
                data=result_data,
                metadata={
                    "api_calls_made": self.api_calls_made,
                    "average_response_time": self.total_response_time / self.api_calls_made,
                    "error_rate": self.error_count / self.api_calls_made
                }
            )
            
        except Exception as e:
            self.error_count += 1
            return ToolResult.error_result(f"API 클라이언트 오류: {str(e)}")
    
    async def _check_rate_limit(self, url: str) -> bool:
        """레이트 리미팅 확인"""
        domain = urlparse(url).netloc
        
        if domain not in self.rate_limits:
            return True
        
        rate_limit = self.rate_limits[domain]
        last_call = self.last_call_times.get(domain, 0)
        current_time = datetime.now().timestamp()
        
        if current_time - last_call < rate_limit:
            return False
        
        self.last_call_times[domain] = current_time
        return True
    
    def _apply_authentication(self, headers: Dict[str, str], auth: Dict[str, Any]):
        """인증 정보 적용"""
        auth_type = auth.get("type", "").lower()
        
        if auth_type == "bearer":
            token = auth.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        
        elif auth_type == "basic":
            username = auth.get("username")
            password = auth.get("password")
            if username and password:
                # 실제 구현에서는 base64 인코딩 사용
                headers["Authorization"] = f"Basic {username}:{password}"
        
        elif auth_type == "api_key":
            api_key = auth.get("api_key")
            key_header = auth.get("key_header", "X-API-Key")
            if api_key:
                headers[key_header] = api_key
        
        elif auth_type == "oauth2":
            token = auth.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
    
    async def _make_request(
        self, 
        url: str, 
        method: str, 
        headers: Dict[str, str], 
        params: Dict[str, Any], 
        data: Optional[Dict[str, Any]], 
        json_data: Optional[Dict[str, Any]], 
        form_data: Optional[Dict[str, Any]], 
        timeout: int, 
        follow_redirects: bool, 
        verify_ssl: bool
    ) -> Dict[str, Any]:
        """HTTP 요청 실행 (시뮬레이션)"""
        try:
            # 실제 구현에서는 aiohttp 사용
            # 여기서는 시뮬레이션
            
            # 네트워크 지연 시뮬레이션
            await asyncio.sleep(0.2)
            
            # 시뮬레이션된 응답 생성
            if "api.example.com" in url:
                response_data = self._generate_example_api_response(method, url)
            elif "shopping" in url.lower():
                response_data = self._generate_shopping_api_response(method, url)
            elif "error" in url.lower():
                return {
                    "success": False,
                    "error": "Simulated API error"
                }
            else:
                response_data = self._generate_generic_api_response(method, url)
            
            return {
                "success": True,
                "status_code": 200,
                "headers": {
                    "content-type": "application/json",
                    "content-length": str(len(json.dumps(response_data)))
                },
                "content": json.dumps(response_data)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_example_api_response(self, method: str, url: str) -> Dict[str, Any]:
        """예제 API 응답 생성"""
        if method == "GET":
            if "/users" in url:
                return {
                    "users": [
                        {"id": 1, "name": "김철수", "email": "kim@example.com"},
                        {"id": 2, "name": "이영희", "email": "lee@example.com"}
                    ],
                    "total": 2
                }
            elif "/products" in url:
                return {
                    "products": [
                        {"id": 1, "name": "상품1", "price": 10000},
                        {"id": 2, "name": "상품2", "price": 20000}
                    ],
                    "total": 2
                }
        
        elif method == "POST":
            return {
                "success": True,
                "message": "리소스가 성공적으로 생성되었습니다",
                "id": 123
            }
        
        elif method == "PUT":
            return {
                "success": True,
                "message": "리소스가 성공적으로 업데이트되었습니다"
            }
        
        elif method == "DELETE":
            return {
                "success": True,
                "message": "리소스가 성공적으로 삭제되었습니다"
            }
        
        return {"message": "API 응답", "method": method, "url": url}
    
    def _generate_shopping_api_response(self, method: str, url: str) -> Dict[str, Any]:
        """쇼핑 API 응답 생성"""
        if method == "GET":
            if "/products" in url:
                return {
                    "products": [
                        {
                            "id": 1,
                            "name": "스마트폰",
                            "price": 899000,
                            "category": "전자제품",
                            "stock": 10,
                            "rating": 4.5
                        },
                        {
                            "id": 2,
                            "name": "노트북",
                            "price": 1299000,
                            "category": "전자제품",
                            "stock": 5,
                            "rating": 4.8
                        }
                    ],
                    "pagination": {
                        "page": 1,
                        "per_page": 10,
                        "total": 2
                    }
                }
            elif "/orders" in url:
                return {
                    "orders": [
                        {
                            "id": 1001,
                            "user_id": 1,
                            "total": 899000,
                            "status": "배송중",
                            "created_at": "2024-01-15T10:30:00Z"
                        }
                    ]
                }
        
        elif method == "POST" and "/orders" in url:
            return {
                "success": True,
                "order_id": 1002,
                "message": "주문이 성공적으로 생성되었습니다",
                "estimated_delivery": "2024-01-20"
            }
        
        return {"message": "쇼핑 API 응답", "method": method}
    
    def _generate_generic_api_response(self, method: str, url: str) -> Dict[str, Any]:
        """일반 API 응답 생성"""
        return {
            "status": "success",
            "message": f"{method} 요청이 성공적으로 처리되었습니다",
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "example_field": "example_value",
                "number_field": 42,
                "boolean_field": True
            }
        }
    
    async def _process_response(
        self, 
        response_data: Dict[str, Any], 
        response_format: str
    ) -> Any:
        """응답 데이터 처리"""
        content = response_data.get("content", "")
        content_type = response_data.get("headers", {}).get("content-type", "")
        
        try:
            if response_format == "json" or (response_format == "auto" and "json" in content_type):
                return json.loads(content) if isinstance(content, str) else content
            
            elif response_format == "text" or response_format == "auto":
                return content
            
            elif response_format == "binary":
                # 바이너리 데이터 처리 (시뮬레이션)
                return {"binary_data": f"<binary content: {len(content)} bytes>"}
            
            else:
                return content
                
        except json.JSONDecodeError:
            if response_format == "json":
                raise ValueError("응답을 JSON으로 파싱할 수 없습니다")
            return content
        except Exception as e:
            self.logger.error(f"응답 처리 실패: {e}")
            return content
    
    @log_function_call
    async def batch_api_calls(self, requests: List[Dict[str, Any]]) -> ToolResult:
        """여러 API 호출 동시 실행"""
        try:
            tasks = []
            for request in requests:
                task = asyncio.create_task(self.execute(**request))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_results = []
            failed_results = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_results.append({
                        "request_index": i,
                        "request": requests[i],
                        "error": str(result)
                    })
                elif isinstance(result, ToolResult) and result.success:
                    successful_results.append({
                        "request_index": i,
                        "request": requests[i],
                        "response": result.data
                    })
                else:
                    failed_results.append({
                        "request_index": i,
                        "request": requests[i],
                        "error": result.error_message if isinstance(result, ToolResult) else "Unknown error"
                    })
            
            return ToolResult.success_result(
                data={
                    "successful_results": successful_results,
                    "failed_results": failed_results,
                    "total_requests": len(requests),
                    "successful_requests": len(successful_results),
                    "failed_requests": len(failed_results)
                }
            )
            
        except Exception as e:
            return ToolResult.error_result(f"배치 API 호출 실패: {str(e)}")
    
    def set_rate_limit(self, domain: str, min_interval: float):
        """도메인별 레이트 리미팅 설정"""
        self.rate_limits[domain] = min_interval
    
    def set_auth_token(self, domain: str, token: str, auth_type: str = "bearer"):
        """도메인별 인증 토큰 설정"""
        self.auth_tokens[domain] = {
            "token": token,
            "type": auth_type
        }
    
    def get_api_statistics(self) -> Dict[str, Any]:
        """API 호출 통계 조회"""
        stats = self.get_statistics()
        stats.update({
            "api_calls_made": self.api_calls_made,
            "total_response_time": self.total_response_time,
            "average_response_time": self.total_response_time / self.api_calls_made if self.api_calls_made > 0 else 0,
            "error_count": self.error_count,
            "error_rate": self.error_count / self.api_calls_made if self.api_calls_made > 0 else 0,
            "success_rate": (self.api_calls_made - self.error_count) / self.api_calls_made if self.api_calls_made > 0 else 0
        })
        return stats