"""웹 스크래퍼 도구 - 웹 페이지 크롤링 및 데이터 추출"""

import asyncio
import re
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin, urlparse
from datetime import datetime

from .base_tool import BaseTool, ToolResult, ToolType, ToolConfig
from core.logger import log_function_call


class WebScraperTool(BaseTool):
    """웹 스크래퍼 도구"""
    
    def __init__(self, config: ToolConfig = None):
        """웹 스크래퍼 초기화"""
        super().__init__("web_scraper", ToolType.WEB_SCRAPER, config)
        
        # 기본 헤더
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # 세션 관리
        self.session = None
        
        # 크롤링 통계
        self.pages_scraped = 0
        self.total_data_size = 0
    
    def get_description(self) -> str:
        """도구 설명 반환"""
        return "웹 페이지를 크롤링하고 데이터를 추출하는 도구입니다. HTML 파싱, CSS 선택자, 정규표현식을 지원합니다."
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        """매개변수 스키마 반환"""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "크롤링할 URL"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST"],
                    "default": "GET",
                    "description": "HTTP 메서드"
                },
                "headers": {
                    "type": "object",
                    "description": "추가 HTTP 헤더"
                },
                "data": {
                    "type": "object",
                    "description": "POST 요청 시 전송할 데이터"
                },
                "selectors": {
                    "type": "object",
                    "description": "CSS 선택자로 추출할 데이터 (키: 필드명, 값: 선택자)"
                },
                "regex_patterns": {
                    "type": "object",
                    "description": "정규표현식으로 추출할 데이터 (키: 필드명, 값: 패턴)"
                },
                "extract_links": {
                    "type": "boolean",
                    "default": False,
                    "description": "페이지의 모든 링크 추출 여부"
                },
                "extract_images": {
                    "type": "boolean",
                    "default": False,
                    "description": "페이지의 모든 이미지 추출 여부"
                },
                "extract_text": {
                    "type": "boolean",
                    "default": True,
                    "description": "페이지의 텍스트 내용 추출 여부"
                },
                "follow_redirects": {
                    "type": "boolean",
                    "default": True,
                    "description": "리다이렉트 따라가기 여부"
                },
                "timeout": {
                    "type": "integer",
                    "default": 30,
                    "description": "요청 타임아웃 (초)"
                },
                "encoding": {
                    "type": "string",
                    "description": "텍스트 인코딩 (자동 감지 시 생략)"
                }
            },
            "required": ["url"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """웹 스크래핑 실행"""
        url = kwargs.get("url")
        method = kwargs.get("method", "GET")
        headers = kwargs.get("headers", {})
        data = kwargs.get("data")
        selectors = kwargs.get("selectors", {})
        regex_patterns = kwargs.get("regex_patterns", {})
        extract_links = kwargs.get("extract_links", False)
        extract_images = kwargs.get("extract_images", False)
        extract_text = kwargs.get("extract_text", True)
        follow_redirects = kwargs.get("follow_redirects", True)
        timeout = kwargs.get("timeout", 30)
        encoding = kwargs.get("encoding")
        
        try:
            # URL 유효성 검사
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return ToolResult.error_result("유효하지 않은 URL입니다")
            
            # HTTP 요청 시뮬레이션 (실제 구현에서는 aiohttp 사용)
            response_data = await self._fetch_page(
                url, method, headers, data, follow_redirects, timeout
            )
            
            if not response_data["success"]:
                return ToolResult.error_result(response_data["error"])
            
            html_content = response_data["content"]
            response_headers = response_data["headers"]
            status_code = response_data["status_code"]
            
            # HTML 파싱 및 데이터 추출
            extracted_data = await self._extract_data(
                html_content, url, selectors, regex_patterns,
                extract_links, extract_images, extract_text, encoding
            )
            
            # 통계 업데이트
            self.pages_scraped += 1
            self.total_data_size += len(html_content)
            
            result_data = {
                "url": url,
                "status_code": status_code,
                "headers": response_headers,
                "content_length": len(html_content),
                "extracted_data": extracted_data,
                "scraped_at": datetime.now().isoformat()
            }
            
            return ToolResult.success_result(
                data=result_data,
                metadata={
                    "pages_scraped": self.pages_scraped,
                    "total_data_size": self.total_data_size
                }
            )
            
        except Exception as e:
            return ToolResult.error_result(f"웹 스크래핑 실패: {str(e)}")
    
    async def _fetch_page(
        self, 
        url: str, 
        method: str, 
        headers: Dict[str, str], 
        data: Optional[Dict[str, Any]], 
        follow_redirects: bool, 
        timeout: int
    ) -> Dict[str, Any]:
        """페이지 가져오기 (시뮬레이션)"""
        try:
            # 실제 구현에서는 aiohttp를 사용
            # 여기서는 시뮬레이션
            
            # 요청 헤더 준비
            request_headers = {**self.default_headers, **headers}
            
            # 네트워크 지연 시뮬레이션
            await asyncio.sleep(0.5)
            
            # 시뮬레이션된 HTML 응답
            if "example.com" in url:
                html_content = self._generate_sample_html(url)
            elif "shopping" in url.lower():
                html_content = self._generate_shopping_html(url)
            else:
                html_content = self._generate_generic_html(url)
            
            return {
                "success": True,
                "content": html_content,
                "headers": {
                    "content-type": "text/html; charset=utf-8",
                    "content-length": str(len(html_content))
                },
                "status_code": 200
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_sample_html(self, url: str) -> str:
        """샘플 HTML 생성"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sample Page</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>Welcome to Sample Page</h1>
            <p class="description">This is a sample page for testing web scraping.</p>
            <div class="content">
                <h2>Features</h2>
                <ul>
                    <li>Web scraping</li>
                    <li>Data extraction</li>
                    <li>HTML parsing</li>
                </ul>
            </div>
            <div class="links">
                <a href="/page1">Page 1</a>
                <a href="/page2">Page 2</a>
                <a href="{url}/about">About</a>
            </div>
            <div class="images">
                <img src="/image1.jpg" alt="Image 1">
                <img src="/image2.png" alt="Image 2">
            </div>
            <footer>
                <p>© 2024 Sample Site</p>
            </footer>
        </body>
        </html>
        """
    
    def _generate_shopping_html(self, url: str) -> str:
        """쇼핑 사이트 HTML 생성"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Shopping Site</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>Online Shopping</h1>
            <div class="products">
                <div class="product" data-id="1">
                    <h3 class="product-name">스마트폰</h3>
                    <p class="price">₩899,000</p>
                    <p class="description">최신 스마트폰입니다.</p>
                    <span class="stock">재고: 10개</span>
                </div>
                <div class="product" data-id="2">
                    <h3 class="product-name">노트북</h3>
                    <p class="price">₩1,299,000</p>
                    <p class="description">고성능 노트북입니다.</p>
                    <span class="stock">재고: 5개</span>
                </div>
                <div class="product" data-id="3">
                    <h3 class="product-name">태블릿</h3>
                    <p class="price">₩599,000</p>
                    <p class="description">휴대용 태블릿입니다.</p>
                    <span class="stock">재고: 15개</span>
                </div>
            </div>
            <div class="categories">
                <a href="/electronics">전자제품</a>
                <a href="/clothing">의류</a>
                <a href="/books">도서</a>
            </div>
        </body>
        </html>
        """
    
    def _generate_generic_html(self, url: str) -> str:
        """일반 HTML 생성"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Generic Page</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>Generic Website</h1>
            <p>This is a generic webpage at {url}</p>
            <div class="content">
                <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
                <p>Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
            </div>
            <nav>
                <a href="/home">Home</a>
                <a href="/about">About</a>
                <a href="/contact">Contact</a>
            </nav>
        </body>
        </html>
        """
    
    async def _extract_data(
        self, 
        html_content: str, 
        base_url: str, 
        selectors: Dict[str, str], 
        regex_patterns: Dict[str, str],
        extract_links: bool, 
        extract_images: bool, 
        extract_text: bool, 
        encoding: Optional[str]
    ) -> Dict[str, Any]:
        """HTML에서 데이터 추출"""
        extracted = {}
        
        try:
            # 실제 구현에서는 BeautifulSoup 또는 lxml 사용
            # 여기서는 간단한 정규표현식 기반 파싱
            
            # CSS 선택자 기반 추출 (시뮬레이션)
            if selectors:
                for field_name, selector in selectors.items():
                    extracted[field_name] = self._extract_by_selector(html_content, selector)
            
            # 정규표현식 기반 추출
            if regex_patterns:
                for field_name, pattern in regex_patterns.items():
                    extracted[field_name] = self._extract_by_regex(html_content, pattern)
            
            # 링크 추출
            if extract_links:
                extracted["links"] = self._extract_links(html_content, base_url)
            
            # 이미지 추출
            if extract_images:
                extracted["images"] = self._extract_images(html_content, base_url)
            
            # 텍스트 추출
            if extract_text:
                extracted["text_content"] = self._extract_text(html_content)
            
            return extracted
            
        except Exception as e:
            self.logger.error(f"데이터 추출 실패: {e}")
            return {"error": str(e)}
    
    def _extract_by_selector(self, html: str, selector: str) -> List[str]:
        """CSS 선택자로 데이터 추출 (시뮬레이션)"""
        results = []
        
        # 간단한 클래스 선택자 처리
        if selector.startswith("."):
            class_name = selector[1:]
            pattern = rf'class="[^"]*{re.escape(class_name)}[^"]*"[^>]*>([^<]+)'
            matches = re.findall(pattern, html, re.IGNORECASE)
            results.extend(matches)
        
        # 태그 선택자 처리
        elif selector.isalpha():
            pattern = rf'<{selector}[^>]*>([^<]+)</{selector}>'
            matches = re.findall(pattern, html, re.IGNORECASE)
            results.extend(matches)
        
        # ID 선택자 처리
        elif selector.startswith("#"):
            id_name = selector[1:]
            pattern = rf'id="{re.escape(id_name)}"[^>]*>([^<]+)'
            matches = re.findall(pattern, html, re.IGNORECASE)
            results.extend(matches)
        
        return [result.strip() for result in results]
    
    def _extract_by_regex(self, html: str, pattern: str) -> List[str]:
        """정규표현식으로 데이터 추출"""
        try:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            return [match.strip() if isinstance(match, str) else str(match).strip() for match in matches]
        except re.error as e:
            self.logger.error(f"정규표현식 오류: {e}")
            return []
    
    def _extract_links(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """링크 추출"""
        links = []
        
        # href 속성을 가진 a 태그 찾기
        pattern = r'<a[^>]+href=["\']([^"\'>]+)["\'][^>]*>([^<]*)</a>'
        matches = re.findall(pattern, html, re.IGNORECASE)
        
        for href, text in matches:
            # 절대 URL로 변환
            absolute_url = urljoin(base_url, href)
            links.append({
                "url": absolute_url,
                "text": text.strip(),
                "href": href
            })
        
        return links
    
    def _extract_images(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """이미지 추출"""
        images = []
        
        # src 속성을 가진 img 태그 찾기
        pattern = r'<img[^>]+src=["\']([^"\'>]+)["\'][^>]*(?:alt=["\']([^"\'>]*)["\'])?[^>]*>'
        matches = re.findall(pattern, html, re.IGNORECASE)
        
        for match in matches:
            src = match[0] if isinstance(match, tuple) else match
            alt = match[1] if isinstance(match, tuple) and len(match) > 1 else ""
            
            # 절대 URL로 변환
            absolute_url = urljoin(base_url, src)
            images.append({
                "url": absolute_url,
                "alt": alt.strip(),
                "src": src
            })
        
        return images
    
    def _extract_text(self, html: str) -> str:
        """HTML에서 텍스트 추출"""
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', html)
        
        # 여러 공백을 하나로 변환
        text = re.sub(r'\s+', ' ', text)
        
        # 앞뒤 공백 제거
        return text.strip()
    
    @log_function_call
    async def scrape_multiple_pages(self, urls: List[str], **common_params) -> ToolResult:
        """여러 페이지 동시 스크래핑"""
        try:
            tasks = []
            for url in urls:
                params = {**common_params, "url": url}
                task = asyncio.create_task(self.execute(**params))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_results = []
            failed_results = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_results.append({
                        "url": urls[i],
                        "error": str(result)
                    })
                elif isinstance(result, ToolResult) and result.success:
                    successful_results.append(result.data)
                else:
                    failed_results.append({
                        "url": urls[i],
                        "error": result.error_message if isinstance(result, ToolResult) else "Unknown error"
                    })
            
            return ToolResult.success_result(
                data={
                    "successful_results": successful_results,
                    "failed_results": failed_results,
                    "total_pages": len(urls),
                    "successful_pages": len(successful_results),
                    "failed_pages": len(failed_results)
                }
            )
            
        except Exception as e:
            return ToolResult.error_result(f"다중 페이지 스크래핑 실패: {str(e)}")
    
    def get_scraping_statistics(self) -> Dict[str, Any]:
        """스크래핑 통계 조회"""
        stats = self.get_statistics()
        stats.update({
            "pages_scraped": self.pages_scraped,
            "total_data_size": self.total_data_size,
            "average_page_size": self.total_data_size / self.pages_scraped if self.pages_scraped > 0 else 0
        })
        return stats