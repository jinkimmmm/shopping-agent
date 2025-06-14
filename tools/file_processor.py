"""파일 처리 도구 - 다양한 파일 형식 읽기/쓰기 및 처리"""

import asyncio
import json
import csv
import os
from typing import Dict, List, Optional, Any, Union, BinaryIO, TextIO
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
import mimetypes

from .base_tool import BaseTool, ToolResult, ToolType, ToolConfig
from core.logger import log_function_call


@dataclass
class FileInfo:
    """파일 정보"""
    path: str
    name: str
    size: int
    mime_type: str
    encoding: Optional[str]
    created_at: datetime
    modified_at: datetime
    is_directory: bool
    permissions: str


@dataclass
class ProcessingResult:
    """파일 처리 결과"""
    success: bool
    data: Any
    file_info: FileInfo
    processing_time: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class FileProcessorTool(BaseTool):
    """파일 처리 도구"""
    
    def __init__(self, config: ToolConfig = None):
        """파일 처리 도구 초기화"""
        super().__init__("file_processor", ToolType.FILE_MANAGER, config)
        
        # 지원하는 파일 형식
        self.supported_formats = {
            "text": [".txt", ".md", ".rst", ".log"],
            "json": [".json", ".jsonl"],
            "csv": [".csv", ".tsv"],
            "xml": [".xml", ".html", ".xhtml"],
            "yaml": [".yaml", ".yml"],
            "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
            "document": [".pdf", ".doc", ".docx", ".odt"],
            "spreadsheet": [".xls", ".xlsx", ".ods"],
            "archive": [".zip", ".tar", ".gz", ".bz2", ".7z"]
        }
        
        # 파일 처리 통계
        self.files_processed = 0
        self.total_processing_time = 0
        self.error_count = 0
        
        # 임시 파일 관리
        self.temp_files = set()
        
        # 파일 캐시
        self.file_cache = {}
        self.cache_enabled = True
    
    def get_description(self) -> str:
        """도구 설명 반환"""
        return "다양한 파일 형식을 읽고 쓰며 처리하는 도구입니다. 텍스트, JSON, CSV, XML, 이미지, 문서 파일을 지원합니다."
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        """매개변수 스키마 반환"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write", "append", "copy", "move", "delete", "list", "info", "search", "convert"],
                    "description": "수행할 작업"
                },
                "file_path": {
                    "type": "string",
                    "description": "파일 경로"
                },
                "target_path": {
                    "type": "string",
                    "description": "대상 파일 경로 (copy, move, convert 액션용)"
                },
                "directory_path": {
                    "type": "string",
                    "description": "디렉토리 경로 (list 액션용)"
                },
                "content": {
                    "type": ["string", "object", "array"],
                    "description": "파일에 쓸 내용"
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "텍스트 파일 인코딩"
                },
                "format": {
                    "type": "string",
                    "enum": ["auto", "text", "json", "csv", "xml", "yaml", "binary"],
                    "default": "auto",
                    "description": "파일 형식"
                },
                "csv_options": {
                    "type": "object",
                    "properties": {
                        "delimiter": {"type": "string", "default": ","},
                        "quotechar": {"type": "string", "default": '"'},
                        "has_header": {"type": "boolean", "default": True},
                        "skip_rows": {"type": "integer", "default": 0}
                    },
                    "description": "CSV 파일 옵션"
                },
                "search_pattern": {
                    "type": "string",
                    "description": "검색 패턴 (search 액션용)"
                },
                "search_options": {
                    "type": "object",
                    "properties": {
                        "case_sensitive": {"type": "boolean", "default": False},
                        "regex": {"type": "boolean", "default": False},
                        "include_line_numbers": {"type": "boolean", "default": True}
                    },
                    "description": "검색 옵션"
                },
                "recursive": {
                    "type": "boolean",
                    "default": False,
                    "description": "하위 디렉토리 포함 여부"
                },
                "create_backup": {
                    "type": "boolean",
                    "default": False,
                    "description": "백업 파일 생성 여부"
                },
                "overwrite": {
                    "type": "boolean",
                    "default": False,
                    "description": "기존 파일 덮어쓰기 여부"
                },
                "use_cache": {
                    "type": "boolean",
                    "default": True,
                    "description": "파일 캐시 사용 여부"
                }
            },
            "required": ["action"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """파일 처리 작업 실행"""
        action = kwargs.get("action")
        
        try:
            if action == "read":
                return await self._handle_read(kwargs)
            elif action == "write":
                return await self._handle_write(kwargs)
            elif action == "append":
                return await self._handle_append(kwargs)
            elif action == "copy":
                return await self._handle_copy(kwargs)
            elif action == "move":
                return await self._handle_move(kwargs)
            elif action == "delete":
                return await self._handle_delete(kwargs)
            elif action == "list":
                return await self._handle_list(kwargs)
            elif action == "info":
                return await self._handle_info(kwargs)
            elif action == "search":
                return await self._handle_search(kwargs)
            elif action == "convert":
                return await self._handle_convert(kwargs)
            else:
                return ToolResult.error_result(f"지원하지 않는 액션: {action}")
                
        except Exception as e:
            self.error_count += 1
            return ToolResult.error_result(f"파일 처리 실패: {str(e)}")
    
    async def _handle_read(self, kwargs: Dict[str, Any]) -> ToolResult:
        """파일 읽기"""
        file_path = kwargs.get("file_path")
        if not file_path:
            return ToolResult.error_result("파일 경로가 필요합니다")
        
        encoding = kwargs.get("encoding", "utf-8")
        file_format = kwargs.get("format", "auto")
        use_cache = kwargs.get("use_cache", True)
        
        try:
            # 파일 존재 확인
            if not await self._file_exists(file_path):
                return ToolResult.error_result(f"파일을 찾을 수 없습니다: {file_path}")
            
            # 캐시 확인
            cache_key = f"{file_path}:{encoding}:{file_format}"
            if use_cache and self.cache_enabled and cache_key in self.file_cache:
                cached_result = self.file_cache[cache_key]
                return ToolResult.success_result(
                    data=cached_result["data"],
                    metadata={**cached_result["metadata"], "from_cache": True}
                )
            
            # 파일 정보 수집
            file_info = await self._get_file_info(file_path)
            
            # 파일 형식 자동 감지
            if file_format == "auto":
                file_format = self._detect_file_format(file_path, file_info.mime_type)
            
            # 파일 읽기
            start_time = datetime.now()
            content = await self._read_file_content(file_path, file_format, encoding)
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            
            # 통계 업데이트
            self.files_processed += 1
            self.total_processing_time += processing_time
            
            result_data = {
                "content": content,
                "file_info": {
                    "path": file_info.path,
                    "name": file_info.name,
                    "size": file_info.size,
                    "mime_type": file_info.mime_type,
                    "encoding": encoding,
                    "format": file_format
                },
                "processing_time": processing_time
            }
            
            # 캐시에 저장
            if use_cache and self.cache_enabled:
                self.file_cache[cache_key] = {
                    "data": result_data,
                    "metadata": {"cached_at": datetime.now().isoformat()}
                }
            
            return ToolResult.success_result(
                data=result_data,
                metadata={"file_format": file_format}
            )
            
        except Exception as e:
            self.error_count += 1
            return ToolResult.error_result(f"파일 읽기 실패: {str(e)}")
    
    async def _handle_write(self, kwargs: Dict[str, Any]) -> ToolResult:
        """파일 쓰기"""
        file_path = kwargs.get("file_path")
        content = kwargs.get("content")
        
        if not file_path:
            return ToolResult.error_result("파일 경로가 필요합니다")
        if content is None:
            return ToolResult.error_result("파일 내용이 필요합니다")
        
        encoding = kwargs.get("encoding", "utf-8")
        file_format = kwargs.get("format", "auto")
        create_backup = kwargs.get("create_backup", False)
        overwrite = kwargs.get("overwrite", False)
        
        try:
            # 파일 존재 확인
            file_exists = await self._file_exists(file_path)
            if file_exists and not overwrite:
                return ToolResult.error_result("파일이 이미 존재합니다. overwrite=True로 설정하세요")
            
            # 백업 생성
            if create_backup and file_exists:
                backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                await self._copy_file(file_path, backup_path)
            
            # 파일 형식 자동 감지
            if file_format == "auto":
                file_format = self._detect_file_format(file_path)
            
            # 디렉토리 생성
            directory = os.path.dirname(file_path)
            if directory and not await self._directory_exists(directory):
                await self._create_directory(directory)
            
            # 파일 쓰기
            start_time = datetime.now()
            await self._write_file_content(file_path, content, file_format, encoding)
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            
            # 통계 업데이트
            self.files_processed += 1
            self.total_processing_time += processing_time
            
            # 파일 정보 수집
            file_info = await self._get_file_info(file_path)
            
            return ToolResult.success_result(
                data={
                    "file_path": file_path,
                    "bytes_written": file_info.size,
                    "format": file_format,
                    "encoding": encoding,
                    "processing_time": processing_time,
                    "backup_created": create_backup and file_exists
                }
            )
            
        except Exception as e:
            self.error_count += 1
            return ToolResult.error_result(f"파일 쓰기 실패: {str(e)}")
    
    async def _handle_append(self, kwargs: Dict[str, Any]) -> ToolResult:
        """파일에 내용 추가"""
        file_path = kwargs.get("file_path")
        content = kwargs.get("content")
        
        if not file_path:
            return ToolResult.error_result("파일 경로가 필요합니다")
        if content is None:
            return ToolResult.error_result("추가할 내용이 필요합니다")
        
        encoding = kwargs.get("encoding", "utf-8")
        
        try:
            # 파일이 없으면 생성
            if not await self._file_exists(file_path):
                directory = os.path.dirname(file_path)
                if directory and not await self._directory_exists(directory):
                    await self._create_directory(directory)
            
            start_time = datetime.now()
            await self._append_file_content(file_path, content, encoding)
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            
            # 통계 업데이트
            self.files_processed += 1
            self.total_processing_time += processing_time
            
            # 파일 정보 수집
            file_info = await self._get_file_info(file_path)
            
            return ToolResult.success_result(
                data={
                    "file_path": file_path,
                    "content_appended": True,
                    "file_size": file_info.size,
                    "processing_time": processing_time
                }
            )
            
        except Exception as e:
            self.error_count += 1
            return ToolResult.error_result(f"파일 추가 실패: {str(e)}")
    
    async def _handle_copy(self, kwargs: Dict[str, Any]) -> ToolResult:
        """파일 복사"""
        file_path = kwargs.get("file_path")
        target_path = kwargs.get("target_path")
        
        if not file_path or not target_path:
            return ToolResult.error_result("원본 파일 경로와 대상 파일 경로가 필요합니다")
        
        overwrite = kwargs.get("overwrite", False)
        
        try:
            # 원본 파일 존재 확인
            if not await self._file_exists(file_path):
                return ToolResult.error_result(f"원본 파일을 찾을 수 없습니다: {file_path}")
            
            # 대상 파일 존재 확인
            if await self._file_exists(target_path) and not overwrite:
                return ToolResult.error_result("대상 파일이 이미 존재합니다. overwrite=True로 설정하세요")
            
            # 대상 디렉토리 생성
            target_directory = os.path.dirname(target_path)
            if target_directory and not await self._directory_exists(target_directory):
                await self._create_directory(target_directory)
            
            start_time = datetime.now()
            await self._copy_file(file_path, target_path)
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            
            # 통계 업데이트
            self.files_processed += 1
            self.total_processing_time += processing_time
            
            # 파일 정보 수집
            source_info = await self._get_file_info(file_path)
            target_info = await self._get_file_info(target_path)
            
            return ToolResult.success_result(
                data={
                    "source_path": file_path,
                    "target_path": target_path,
                    "bytes_copied": source_info.size,
                    "processing_time": processing_time,
                    "source_info": {
                        "size": source_info.size,
                        "modified_at": source_info.modified_at.isoformat()
                    },
                    "target_info": {
                        "size": target_info.size,
                        "modified_at": target_info.modified_at.isoformat()
                    }
                }
            )
            
        except Exception as e:
            self.error_count += 1
            return ToolResult.error_result(f"파일 복사 실패: {str(e)}")
    
    async def _handle_move(self, kwargs: Dict[str, Any]) -> ToolResult:
        """파일 이동"""
        file_path = kwargs.get("file_path")
        target_path = kwargs.get("target_path")
        
        if not file_path or not target_path:
            return ToolResult.error_result("원본 파일 경로와 대상 파일 경로가 필요합니다")
        
        overwrite = kwargs.get("overwrite", False)
        
        try:
            # 원본 파일 존재 확인
            if not await self._file_exists(file_path):
                return ToolResult.error_result(f"원본 파일을 찾을 수 없습니다: {file_path}")
            
            # 대상 파일 존재 확인
            if await self._file_exists(target_path) and not overwrite:
                return ToolResult.error_result("대상 파일이 이미 존재합니다. overwrite=True로 설정하세요")
            
            # 파일 정보 수집 (이동 전)
            source_info = await self._get_file_info(file_path)
            
            # 대상 디렉토리 생성
            target_directory = os.path.dirname(target_path)
            if target_directory and not await self._directory_exists(target_directory):
                await self._create_directory(target_directory)
            
            start_time = datetime.now()
            await self._move_file(file_path, target_path)
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            
            # 통계 업데이트
            self.files_processed += 1
            self.total_processing_time += processing_time
            
            return ToolResult.success_result(
                data={
                    "source_path": file_path,
                    "target_path": target_path,
                    "bytes_moved": source_info.size,
                    "processing_time": processing_time
                }
            )
            
        except Exception as e:
            self.error_count += 1
            return ToolResult.error_result(f"파일 이동 실패: {str(e)}")
    
    async def _handle_delete(self, kwargs: Dict[str, Any]) -> ToolResult:
        """파일 삭제"""
        file_path = kwargs.get("file_path")
        if not file_path:
            return ToolResult.error_result("파일 경로가 필요합니다")
        
        create_backup = kwargs.get("create_backup", False)
        
        try:
            # 파일 존재 확인
            if not await self._file_exists(file_path):
                return ToolResult.error_result(f"파일을 찾을 수 없습니다: {file_path}")
            
            # 파일 정보 수집 (삭제 전)
            file_info = await self._get_file_info(file_path)
            
            # 백업 생성
            backup_path = None
            if create_backup:
                backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                await self._copy_file(file_path, backup_path)
            
            start_time = datetime.now()
            await self._delete_file(file_path)
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            
            # 통계 업데이트
            self.files_processed += 1
            self.total_processing_time += processing_time
            
            return ToolResult.success_result(
                data={
                    "deleted_path": file_path,
                    "file_size": file_info.size,
                    "backup_path": backup_path,
                    "processing_time": processing_time
                }
            )
            
        except Exception as e:
            self.error_count += 1
            return ToolResult.error_result(f"파일 삭제 실패: {str(e)}")
    
    async def _handle_list(self, kwargs: Dict[str, Any]) -> ToolResult:
        """디렉토리 목록 조회"""
        directory_path = kwargs.get("directory_path", ".")
        recursive = kwargs.get("recursive", False)
        
        try:
            if not await self._directory_exists(directory_path):
                return ToolResult.error_result(f"디렉토리를 찾을 수 없습니다: {directory_path}")
            
            start_time = datetime.now()
            file_list = await self._list_directory(directory_path, recursive)
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            
            # 파일 통계
            total_files = len([f for f in file_list if not f["is_directory"]])
            total_directories = len([f for f in file_list if f["is_directory"]])
            total_size = sum(f["size"] for f in file_list if not f["is_directory"])
            
            return ToolResult.success_result(
                data={
                    "directory_path": directory_path,
                    "files": file_list,
                    "statistics": {
                        "total_files": total_files,
                        "total_directories": total_directories,
                        "total_size": total_size
                    },
                    "processing_time": processing_time
                }
            )
            
        except Exception as e:
            return ToolResult.error_result(f"디렉토리 목록 조회 실패: {str(e)}")
    
    async def _handle_info(self, kwargs: Dict[str, Any]) -> ToolResult:
        """파일 정보 조회"""
        file_path = kwargs.get("file_path")
        if not file_path:
            return ToolResult.error_result("파일 경로가 필요합니다")
        
        try:
            if not await self._file_exists(file_path):
                return ToolResult.error_result(f"파일을 찾을 수 없습니다: {file_path}")
            
            file_info = await self._get_file_info(file_path)
            
            return ToolResult.success_result(
                data={
                    "path": file_info.path,
                    "name": file_info.name,
                    "size": file_info.size,
                    "mime_type": file_info.mime_type,
                    "encoding": file_info.encoding,
                    "created_at": file_info.created_at.isoformat(),
                    "modified_at": file_info.modified_at.isoformat(),
                    "is_directory": file_info.is_directory,
                    "permissions": file_info.permissions,
                    "file_format": self._detect_file_format(file_path, file_info.mime_type)
                }
            )
            
        except Exception as e:
            return ToolResult.error_result(f"파일 정보 조회 실패: {str(e)}")
    
    async def _handle_search(self, kwargs: Dict[str, Any]) -> ToolResult:
        """파일 내용 검색"""
        file_path = kwargs.get("file_path")
        search_pattern = kwargs.get("search_pattern")
        
        if not file_path or not search_pattern:
            return ToolResult.error_result("파일 경로와 검색 패턴이 필요합니다")
        
        search_options = kwargs.get("search_options", {})
        encoding = kwargs.get("encoding", "utf-8")
        
        try:
            if not await self._file_exists(file_path):
                return ToolResult.error_result(f"파일을 찾을 수 없습니다: {file_path}")
            
            start_time = datetime.now()
            search_results = await self._search_file_content(
                file_path, search_pattern, search_options, encoding
            )
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            
            return ToolResult.success_result(
                data={
                    "file_path": file_path,
                    "search_pattern": search_pattern,
                    "matches": search_results,
                    "match_count": len(search_results),
                    "processing_time": processing_time
                }
            )
            
        except Exception as e:
            return ToolResult.error_result(f"파일 검색 실패: {str(e)}")
    
    async def _handle_convert(self, kwargs: Dict[str, Any]) -> ToolResult:
        """파일 형식 변환"""
        file_path = kwargs.get("file_path")
        target_path = kwargs.get("target_path")
        
        if not file_path or not target_path:
            return ToolResult.error_result("원본 파일 경로와 대상 파일 경로가 필요합니다")
        
        try:
            if not await self._file_exists(file_path):
                return ToolResult.error_result(f"원본 파일을 찾을 수 없습니다: {file_path}")
            
            # 파일 형식 감지
            source_format = self._detect_file_format(file_path)
            target_format = self._detect_file_format(target_path)
            
            start_time = datetime.now()
            conversion_result = await self._convert_file_format(
                file_path, target_path, source_format, target_format
            )
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            
            if conversion_result["success"]:
                # 통계 업데이트
                self.files_processed += 1
                self.total_processing_time += processing_time
                
                return ToolResult.success_result(
                    data={
                        "source_path": file_path,
                        "target_path": target_path,
                        "source_format": source_format,
                        "target_format": target_format,
                        "processing_time": processing_time,
                        "conversion_info": conversion_result["info"]
                    }
                )
            else:
                return ToolResult.error_result(conversion_result["error"])
            
        except Exception as e:
            self.error_count += 1
            return ToolResult.error_result(f"파일 변환 실패: {str(e)}")
    
    # 헬퍼 메서드들 (시뮬레이션)
    
    async def _file_exists(self, file_path: str) -> bool:
        """파일 존재 확인 (시뮬레이션)"""
        # 실제 구현에서는 os.path.exists 사용
        return True  # 시뮬레이션에서는 항상 존재한다고 가정
    
    async def _directory_exists(self, directory_path: str) -> bool:
        """디렉토리 존재 확인 (시뮬레이션)"""
        return True
    
    async def _create_directory(self, directory_path: str):
        """디렉토리 생성 (시뮬레이션)"""
        await asyncio.sleep(0.01)
    
    async def _get_file_info(self, file_path: str) -> FileInfo:
        """파일 정보 수집 (시뮬레이션)"""
        await asyncio.sleep(0.01)
        
        # 시뮬레이션된 파일 정보
        file_name = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        
        return FileInfo(
            path=file_path,
            name=file_name,
            size=1024,  # 시뮬레이션
            mime_type=mime_type or "application/octet-stream",
            encoding="utf-8",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            is_directory=False,
            permissions="rw-r--r--"
        )
    
    def _detect_file_format(self, file_path: str, mime_type: str = None) -> str:
        """파일 형식 자동 감지"""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        for format_type, extensions in self.supported_formats.items():
            if file_ext in extensions:
                return format_type
        
        # MIME 타입으로 추가 감지
        if mime_type:
            if mime_type.startswith("text/"):
                return "text"
            elif mime_type == "application/json":
                return "json"
            elif mime_type == "text/csv":
                return "csv"
            elif mime_type.startswith("image/"):
                return "image"
        
        return "binary"
    
    async def _read_file_content(self, file_path: str, file_format: str, encoding: str) -> Any:
        """파일 내용 읽기 (시뮬레이션)"""
        await asyncio.sleep(0.02)
        
        # 시뮬레이션된 파일 내용
        if file_format == "json":
            return {"example": "data", "timestamp": datetime.now().isoformat()}
        elif file_format == "csv":
            return [
                {"id": 1, "name": "상품1", "price": 10000},
                {"id": 2, "name": "상품2", "price": 20000}
            ]
        elif file_format == "text":
            return f"파일 내용: {file_path}\n생성 시간: {datetime.now().isoformat()}"
        else:
            return f"파일 내용 ({file_format}): {os.path.basename(file_path)}"
    
    async def _write_file_content(self, file_path: str, content: Any, file_format: str, encoding: str):
        """파일 내용 쓰기 (시뮬레이션)"""
        await asyncio.sleep(0.02)
        # 실제 구현에서는 파일 형식에 따라 적절히 저장
    
    async def _append_file_content(self, file_path: str, content: Any, encoding: str):
        """파일에 내용 추가 (시뮬레이션)"""
        await asyncio.sleep(0.01)
    
    async def _copy_file(self, source_path: str, target_path: str):
        """파일 복사 (시뮬레이션)"""
        await asyncio.sleep(0.05)
    
    async def _move_file(self, source_path: str, target_path: str):
        """파일 이동 (시뮬레이션)"""
        await asyncio.sleep(0.03)
    
    async def _delete_file(self, file_path: str):
        """파일 삭제 (시뮬레이션)"""
        await asyncio.sleep(0.01)
    
    async def _list_directory(self, directory_path: str, recursive: bool) -> List[Dict[str, Any]]:
        """디렉토리 목록 조회 (시뮬레이션)"""
        await asyncio.sleep(0.02)
        
        # 시뮬레이션된 파일 목록
        return [
            {
                "name": "file1.txt",
                "path": os.path.join(directory_path, "file1.txt"),
                "size": 1024,
                "is_directory": False,
                "modified_at": datetime.now().isoformat()
            },
            {
                "name": "data.json",
                "path": os.path.join(directory_path, "data.json"),
                "size": 2048,
                "is_directory": False,
                "modified_at": datetime.now().isoformat()
            },
            {
                "name": "subdirectory",
                "path": os.path.join(directory_path, "subdirectory"),
                "size": 0,
                "is_directory": True,
                "modified_at": datetime.now().isoformat()
            }
        ]
    
    async def _search_file_content(
        self, 
        file_path: str, 
        pattern: str, 
        options: Dict[str, Any], 
        encoding: str
    ) -> List[Dict[str, Any]]:
        """파일 내용 검색 (시뮬레이션)"""
        await asyncio.sleep(0.03)
        
        # 시뮬레이션된 검색 결과
        return [
            {
                "line_number": 5,
                "line_content": f"이 줄에 '{pattern}' 패턴이 포함되어 있습니다.",
                "match_start": 10,
                "match_end": 10 + len(pattern)
            },
            {
                "line_number": 12,
                "line_content": f"또 다른 '{pattern}' 매치입니다.",
                "match_start": 8,
                "match_end": 8 + len(pattern)
            }
        ]
    
    async def _convert_file_format(
        self, 
        source_path: str, 
        target_path: str, 
        source_format: str, 
        target_format: str
    ) -> Dict[str, Any]:
        """파일 형식 변환 (시뮬레이션)"""
        await asyncio.sleep(0.1)
        
        # 지원하는 변환 확인
        supported_conversions = {
            ("csv", "json"): True,
            ("json", "csv"): True,
            ("text", "json"): True,
            ("yaml", "json"): True,
            ("json", "yaml"): True
        }
        
        conversion_key = (source_format, target_format)
        if conversion_key in supported_conversions:
            return {
                "success": True,
                "info": {
                    "conversion_type": f"{source_format} -> {target_format}",
                    "records_converted": 100  # 시뮬레이션
                }
            }
        else:
            return {
                "success": False,
                "error": f"지원하지 않는 변환: {source_format} -> {target_format}"
            }
    
    @log_function_call
    def clear_cache(self):
        """파일 캐시 초기화"""
        self.file_cache.clear()
        self.logger.info("파일 캐시가 초기화되었습니다")
    
    def get_file_statistics(self) -> Dict[str, Any]:
        """파일 처리 통계 조회"""
        stats = self.get_statistics()
        stats.update({
            "files_processed": self.files_processed,
            "total_processing_time": self.total_processing_time,
            "average_processing_time": self.total_processing_time / self.files_processed if self.files_processed > 0 else 0,
            "error_count": self.error_count,
            "error_rate": self.error_count / self.files_processed if self.files_processed > 0 else 0,
            "cache_size": len(self.file_cache),
            "cache_enabled": self.cache_enabled,
            "supported_formats": list(self.supported_formats.keys())
        })
        return stats