"""데이터베이스 도구 - 다양한 데이터베이스 연결 및 쿼리 실행"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass

from .base_tool import BaseTool, ToolResult, ToolType, ToolConfig
from core.logger import log_function_call


@dataclass
class DatabaseConnection:
    """데이터베이스 연결 정보"""
    host: str
    port: int
    database: str
    username: str
    password: str
    db_type: str  # postgresql, mysql, sqlite, mongodb
    connection_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.connection_params is None:
            self.connection_params = {}


@dataclass
class QueryResult:
    """쿼리 결과"""
    success: bool
    data: List[Dict[str, Any]]
    affected_rows: int
    execution_time: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DatabaseTool(BaseTool):
    """데이터베이스 도구"""
    
    def __init__(self, config: ToolConfig = None):
        """데이터베이스 도구 초기화"""
        super().__init__("database_tool", ToolType.DATABASE, config)
        
        # 연결 풀
        self.connections = {}
        
        # 쿼리 통계
        self.queries_executed = 0
        self.total_execution_time = 0
        self.error_count = 0
        
        # 트랜잭션 관리
        self.active_transactions = {}
        
        # 쿼리 캐시
        self.query_cache = {}
        self.cache_enabled = True
    
    def get_description(self) -> str:
        """도구 설명 반환"""
        return "다양한 데이터베이스에 연결하고 SQL 쿼리를 실행하는 도구입니다. PostgreSQL, MySQL, SQLite, MongoDB를 지원합니다."
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        """매개변수 스키마 반환"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["connect", "query", "execute", "transaction", "disconnect", "list_tables", "describe_table"],
                    "description": "수행할 작업"
                },
                "connection_id": {
                    "type": "string",
                    "description": "연결 식별자"
                },
                "connection": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string", "description": "데이터베이스 호스트"},
                        "port": {"type": "integer", "description": "포트 번호"},
                        "database": {"type": "string", "description": "데이터베이스명"},
                        "username": {"type": "string", "description": "사용자명"},
                        "password": {"type": "string", "description": "비밀번호"},
                        "db_type": {
                            "type": "string",
                            "enum": ["postgresql", "mysql", "sqlite", "mongodb"],
                            "description": "데이터베이스 타입"
                        },
                        "connection_params": {
                            "type": "object",
                            "description": "추가 연결 매개변수"
                        }
                    },
                    "required": ["host", "database", "username", "db_type"],
                    "description": "데이터베이스 연결 정보"
                },
                "query": {
                    "type": "string",
                    "description": "실행할 SQL 쿼리"
                },
                "parameters": {
                    "type": "array",
                    "description": "쿼리 매개변수"
                },
                "transaction_queries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "parameters": {"type": "array"}
                        },
                        "required": ["query"]
                    },
                    "description": "트랜잭션으로 실행할 쿼리 목록"
                },
                "table_name": {
                    "type": "string",
                    "description": "테이블명 (describe_table 액션용)"
                },
                "fetch_size": {
                    "type": "integer",
                    "default": 1000,
                    "description": "한 번에 가져올 레코드 수"
                },
                "use_cache": {
                    "type": "boolean",
                    "default": True,
                    "description": "쿼리 캐시 사용 여부"
                },
                "timeout": {
                    "type": "integer",
                    "default": 30,
                    "description": "쿼리 타임아웃 (초)"
                }
            },
            "required": ["action"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """데이터베이스 작업 실행"""
        action = kwargs.get("action")
        connection_id = kwargs.get("connection_id", "default")
        
        try:
            if action == "connect":
                return await self._handle_connect(connection_id, kwargs)
            elif action == "query":
                return await self._handle_query(connection_id, kwargs)
            elif action == "execute":
                return await self._handle_execute(connection_id, kwargs)
            elif action == "transaction":
                return await self._handle_transaction(connection_id, kwargs)
            elif action == "disconnect":
                return await self._handle_disconnect(connection_id)
            elif action == "list_tables":
                return await self._handle_list_tables(connection_id)
            elif action == "describe_table":
                return await self._handle_describe_table(connection_id, kwargs)
            else:
                return ToolResult.error_result(f"지원하지 않는 액션: {action}")
                
        except Exception as e:
            self.error_count += 1
            return ToolResult.error_result(f"데이터베이스 작업 실패: {str(e)}")
    
    async def _handle_connect(self, connection_id: str, kwargs: Dict[str, Any]) -> ToolResult:
        """데이터베이스 연결"""
        connection_info = kwargs.get("connection")
        if not connection_info:
            return ToolResult.error_result("연결 정보가 필요합니다")
        
        try:
            # 연결 정보 생성
            db_connection = DatabaseConnection(
                host=connection_info.get("host"),
                port=connection_info.get("port", self._get_default_port(connection_info.get("db_type"))),
                database=connection_info.get("database"),
                username=connection_info.get("username"),
                password=connection_info.get("password", ""),
                db_type=connection_info.get("db_type"),
                connection_params=connection_info.get("connection_params", {})
            )
            
            # 연결 시뮬레이션
            connection_result = await self._simulate_connection(db_connection)
            
            if connection_result["success"]:
                self.connections[connection_id] = db_connection
                
                return ToolResult.success_result(
                    data={
                        "connection_id": connection_id,
                        "database_type": db_connection.db_type,
                        "host": db_connection.host,
                        "database": db_connection.database,
                        "connected_at": datetime.now().isoformat()
                    },
                    metadata={"connection_info": connection_result["info"]}
                )
            else:
                return ToolResult.error_result(connection_result["error"])
                
        except Exception as e:
            return ToolResult.error_result(f"연결 실패: {str(e)}")
    
    async def _handle_query(self, connection_id: str, kwargs: Dict[str, Any]) -> ToolResult:
        """SELECT 쿼리 실행"""
        if connection_id not in self.connections:
            return ToolResult.error_result("연결이 존재하지 않습니다")
        
        query = kwargs.get("query")
        parameters = kwargs.get("parameters", [])
        fetch_size = kwargs.get("fetch_size", 1000)
        use_cache = kwargs.get("use_cache", True)
        timeout = kwargs.get("timeout", 30)
        
        if not query:
            return ToolResult.error_result("쿼리가 필요합니다")
        
        try:
            # 캐시 확인
            cache_key = self._generate_cache_key(query, parameters)
            if use_cache and self.cache_enabled and cache_key in self.query_cache:
                cached_result = self.query_cache[cache_key]
                return ToolResult.success_result(
                    data=cached_result,
                    metadata={"from_cache": True}
                )
            
            # 쿼리 실행
            start_time = datetime.now()
            result = await self._execute_query(
                self.connections[connection_id], query, parameters, fetch_size, timeout
            )
            end_time = datetime.now()
            
            execution_time = (end_time - start_time).total_seconds()
            
            # 통계 업데이트
            self.queries_executed += 1
            self.total_execution_time += execution_time
            
            if result.success:
                # 캐시에 저장
                if use_cache and self.cache_enabled:
                    self.query_cache[cache_key] = result.data
                
                return ToolResult.success_result(
                    data={
                        "rows": result.data,
                        "row_count": len(result.data),
                        "execution_time": execution_time,
                        "query": query
                    },
                    metadata=result.metadata
                )
            else:
                self.error_count += 1
                return ToolResult.error_result(result.error_message)
                
        except Exception as e:
            self.error_count += 1
            return ToolResult.error_result(f"쿼리 실행 실패: {str(e)}")
    
    async def _handle_execute(self, connection_id: str, kwargs: Dict[str, Any]) -> ToolResult:
        """INSERT/UPDATE/DELETE 쿼리 실행"""
        if connection_id not in self.connections:
            return ToolResult.error_result("연결이 존재하지 않습니다")
        
        query = kwargs.get("query")
        parameters = kwargs.get("parameters", [])
        timeout = kwargs.get("timeout", 30)
        
        if not query:
            return ToolResult.error_result("쿼리가 필요합니다")
        
        try:
            start_time = datetime.now()
            result = await self._execute_non_query(
                self.connections[connection_id], query, parameters, timeout
            )
            end_time = datetime.now()
            
            execution_time = (end_time - start_time).total_seconds()
            
            # 통계 업데이트
            self.queries_executed += 1
            self.total_execution_time += execution_time
            
            if result.success:
                return ToolResult.success_result(
                    data={
                        "affected_rows": result.affected_rows,
                        "execution_time": execution_time,
                        "query": query
                    },
                    metadata=result.metadata
                )
            else:
                self.error_count += 1
                return ToolResult.error_result(result.error_message)
                
        except Exception as e:
            self.error_count += 1
            return ToolResult.error_result(f"쿼리 실행 실패: {str(e)}")
    
    async def _handle_transaction(self, connection_id: str, kwargs: Dict[str, Any]) -> ToolResult:
        """트랜잭션 실행"""
        if connection_id not in self.connections:
            return ToolResult.error_result("연결이 존재하지 않습니다")
        
        transaction_queries = kwargs.get("transaction_queries", [])
        if not transaction_queries:
            return ToolResult.error_result("트랜잭션 쿼리가 필요합니다")
        
        try:
            start_time = datetime.now()
            results = await self._execute_transaction(
                self.connections[connection_id], transaction_queries
            )
            end_time = datetime.now()
            
            execution_time = (end_time - start_time).total_seconds()
            
            # 통계 업데이트
            self.queries_executed += len(transaction_queries)
            self.total_execution_time += execution_time
            
            total_affected_rows = sum(r.get("affected_rows", 0) for r in results if r.get("success"))
            
            return ToolResult.success_result(
                data={
                    "transaction_results": results,
                    "total_queries": len(transaction_queries),
                    "total_affected_rows": total_affected_rows,
                    "execution_time": execution_time
                }
            )
            
        except Exception as e:
            self.error_count += 1
            return ToolResult.error_result(f"트랜잭션 실행 실패: {str(e)}")
    
    async def _handle_disconnect(self, connection_id: str) -> ToolResult:
        """연결 해제"""
        if connection_id not in self.connections:
            return ToolResult.error_result("연결이 존재하지 않습니다")
        
        try:
            # 연결 해제 시뮬레이션
            del self.connections[connection_id]
            
            # 활성 트랜잭션 정리
            if connection_id in self.active_transactions:
                del self.active_transactions[connection_id]
            
            return ToolResult.success_result(
                data={
                    "connection_id": connection_id,
                    "disconnected_at": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            return ToolResult.error_result(f"연결 해제 실패: {str(e)}")
    
    async def _handle_list_tables(self, connection_id: str) -> ToolResult:
        """테이블 목록 조회"""
        if connection_id not in self.connections:
            return ToolResult.error_result("연결이 존재하지 않습니다")
        
        try:
            connection = self.connections[connection_id]
            tables = await self._get_table_list(connection)
            
            return ToolResult.success_result(
                data={
                    "tables": tables,
                    "table_count": len(tables),
                    "database": connection.database
                }
            )
            
        except Exception as e:
            return ToolResult.error_result(f"테이블 목록 조회 실패: {str(e)}")
    
    async def _handle_describe_table(self, connection_id: str, kwargs: Dict[str, Any]) -> ToolResult:
        """테이블 구조 조회"""
        if connection_id not in self.connections:
            return ToolResult.error_result("연결이 존재하지 않습니다")
        
        table_name = kwargs.get("table_name")
        if not table_name:
            return ToolResult.error_result("테이블명이 필요합니다")
        
        try:
            connection = self.connections[connection_id]
            table_info = await self._describe_table(connection, table_name)
            
            return ToolResult.success_result(
                data={
                    "table_name": table_name,
                    "columns": table_info["columns"],
                    "indexes": table_info["indexes"],
                    "constraints": table_info["constraints"]
                }
            )
            
        except Exception as e:
            return ToolResult.error_result(f"테이블 구조 조회 실패: {str(e)}")
    
    def _get_default_port(self, db_type: str) -> int:
        """데이터베이스 타입별 기본 포트 반환"""
        default_ports = {
            "postgresql": 5432,
            "mysql": 3306,
            "sqlite": 0,  # SQLite는 파일 기반
            "mongodb": 27017
        }
        return default_ports.get(db_type, 5432)
    
    async def _simulate_connection(self, connection: DatabaseConnection) -> Dict[str, Any]:
        """데이터베이스 연결 시뮬레이션"""
        try:
            # 연결 지연 시뮬레이션
            await asyncio.sleep(0.1)
            
            # 시뮬레이션된 연결 성공
            return {
                "success": True,
                "info": {
                    "server_version": self._get_simulated_version(connection.db_type),
                    "connection_time": datetime.now().isoformat(),
                    "charset": "utf8mb4" if connection.db_type == "mysql" else "UTF8"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_simulated_version(self, db_type: str) -> str:
        """시뮬레이션된 데이터베이스 버전 반환"""
        versions = {
            "postgresql": "PostgreSQL 14.5",
            "mysql": "MySQL 8.0.30",
            "sqlite": "SQLite 3.39.0",
            "mongodb": "MongoDB 6.0.2"
        }
        return versions.get(db_type, "Unknown")
    
    async def _execute_query(
        self, 
        connection: DatabaseConnection, 
        query: str, 
        parameters: List[Any], 
        fetch_size: int, 
        timeout: int
    ) -> QueryResult:
        """SELECT 쿼리 실행 (시뮬레이션)"""
        try:
            # 쿼리 실행 시뮬레이션
            await asyncio.sleep(0.05)  # 실행 지연
            
            # 시뮬레이션된 결과 생성
            if "users" in query.lower():
                data = [
                    {"id": 1, "name": "김철수", "email": "kim@example.com", "created_at": "2024-01-01"},
                    {"id": 2, "name": "이영희", "email": "lee@example.com", "created_at": "2024-01-02"}
                ]
            elif "products" in query.lower():
                data = [
                    {"id": 1, "name": "스마트폰", "price": 899000, "category": "전자제품"},
                    {"id": 2, "name": "노트북", "price": 1299000, "category": "전자제품"}
                ]
            elif "orders" in query.lower():
                data = [
                    {"id": 1001, "user_id": 1, "total": 899000, "status": "완료"},
                    {"id": 1002, "user_id": 2, "total": 1299000, "status": "배송중"}
                ]
            else:
                data = [{"result": "쿼리가 성공적으로 실행되었습니다", "timestamp": datetime.now().isoformat()}]
            
            return QueryResult(
                success=True,
                data=data[:fetch_size],
                affected_rows=0,
                execution_time=0.05,
                metadata={"query_type": "SELECT"}
            )
            
        except Exception as e:
            return QueryResult(
                success=False,
                data=[],
                affected_rows=0,
                execution_time=0,
                error_message=str(e)
            )
    
    async def _execute_non_query(
        self, 
        connection: DatabaseConnection, 
        query: str, 
        parameters: List[Any], 
        timeout: int
    ) -> QueryResult:
        """INSERT/UPDATE/DELETE 쿼리 실행 (시뮬레이션)"""
        try:
            # 쿼리 실행 시뮬레이션
            await asyncio.sleep(0.02)
            
            # 영향받은 행 수 시뮬레이션
            if "insert" in query.lower():
                affected_rows = 1
                query_type = "INSERT"
            elif "update" in query.lower():
                affected_rows = 2
                query_type = "UPDATE"
            elif "delete" in query.lower():
                affected_rows = 1
                query_type = "DELETE"
            else:
                affected_rows = 0
                query_type = "OTHER"
            
            return QueryResult(
                success=True,
                data=[],
                affected_rows=affected_rows,
                execution_time=0.02,
                metadata={"query_type": query_type}
            )
            
        except Exception as e:
            return QueryResult(
                success=False,
                data=[],
                affected_rows=0,
                execution_time=0,
                error_message=str(e)
            )
    
    async def _execute_transaction(
        self, 
        connection: DatabaseConnection, 
        queries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """트랜잭션 실행 (시뮬레이션)"""
        results = []
        
        try:
            # 트랜잭션 시작 시뮬레이션
            await asyncio.sleep(0.01)
            
            for i, query_info in enumerate(queries):
                query = query_info.get("query")
                parameters = query_info.get("parameters", [])
                
                try:
                    # 각 쿼리 실행
                    if query.lower().strip().startswith("select"):
                        result = await self._execute_query(connection, query, parameters, 1000, 30)
                    else:
                        result = await self._execute_non_query(connection, query, parameters, 30)
                    
                    if result.success:
                        results.append({
                            "query_index": i,
                            "success": True,
                            "affected_rows": result.affected_rows,
                            "data": result.data
                        })
                    else:
                        # 트랜잭션 롤백 시뮬레이션
                        results.append({
                            "query_index": i,
                            "success": False,
                            "error": result.error_message
                        })
                        break
                        
                except Exception as e:
                    results.append({
                        "query_index": i,
                        "success": False,
                        "error": str(e)
                    })
                    break
            
            # 트랜잭션 커밋/롤백 시뮬레이션
            await asyncio.sleep(0.01)
            
            return results
            
        except Exception as e:
            return [{"success": False, "error": f"트랜잭션 실패: {str(e)}"}]
    
    async def _get_table_list(self, connection: DatabaseConnection) -> List[Dict[str, Any]]:
        """테이블 목록 조회 (시뮬레이션)"""
        # 시뮬레이션된 테이블 목록
        tables = [
            {"table_name": "users", "table_type": "BASE TABLE", "engine": "InnoDB"},
            {"table_name": "products", "table_type": "BASE TABLE", "engine": "InnoDB"},
            {"table_name": "orders", "table_type": "BASE TABLE", "engine": "InnoDB"},
            {"table_name": "order_items", "table_type": "BASE TABLE", "engine": "InnoDB"}
        ]
        
        await asyncio.sleep(0.02)
        return tables
    
    async def _describe_table(self, connection: DatabaseConnection, table_name: str) -> Dict[str, Any]:
        """테이블 구조 조회 (시뮬레이션)"""
        # 시뮬레이션된 테이블 구조
        table_structures = {
            "users": {
                "columns": [
                    {"column_name": "id", "data_type": "int", "is_nullable": False, "is_primary_key": True},
                    {"column_name": "name", "data_type": "varchar(100)", "is_nullable": False, "is_primary_key": False},
                    {"column_name": "email", "data_type": "varchar(255)", "is_nullable": False, "is_primary_key": False},
                    {"column_name": "created_at", "data_type": "timestamp", "is_nullable": False, "is_primary_key": False}
                ],
                "indexes": [
                    {"index_name": "PRIMARY", "columns": ["id"], "is_unique": True},
                    {"index_name": "idx_email", "columns": ["email"], "is_unique": True}
                ],
                "constraints": [
                    {"constraint_name": "PRIMARY", "constraint_type": "PRIMARY KEY", "columns": ["id"]}
                ]
            },
            "products": {
                "columns": [
                    {"column_name": "id", "data_type": "int", "is_nullable": False, "is_primary_key": True},
                    {"column_name": "name", "data_type": "varchar(200)", "is_nullable": False, "is_primary_key": False},
                    {"column_name": "price", "data_type": "decimal(10,2)", "is_nullable": False, "is_primary_key": False},
                    {"column_name": "category", "data_type": "varchar(100)", "is_nullable": True, "is_primary_key": False}
                ],
                "indexes": [
                    {"index_name": "PRIMARY", "columns": ["id"], "is_unique": True},
                    {"index_name": "idx_category", "columns": ["category"], "is_unique": False}
                ],
                "constraints": [
                    {"constraint_name": "PRIMARY", "constraint_type": "PRIMARY KEY", "columns": ["id"]}
                ]
            }
        }
        
        await asyncio.sleep(0.02)
        return table_structures.get(table_name, {
            "columns": [],
            "indexes": [],
            "constraints": []
        })
    
    def _generate_cache_key(self, query: str, parameters: List[Any]) -> str:
        """쿼리 캐시 키 생성"""
        import hashlib
        content = f"{query}:{json.dumps(parameters, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    @log_function_call
    def clear_cache(self):
        """쿼리 캐시 초기화"""
        self.query_cache.clear()
        self.logger.info("쿼리 캐시가 초기화되었습니다")
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """데이터베이스 통계 조회"""
        stats = self.get_statistics()
        stats.update({
            "queries_executed": self.queries_executed,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": self.total_execution_time / self.queries_executed if self.queries_executed > 0 else 0,
            "error_count": self.error_count,
            "error_rate": self.error_count / self.queries_executed if self.queries_executed > 0 else 0,
            "active_connections": len(self.connections),
            "cache_size": len(self.query_cache),
            "cache_enabled": self.cache_enabled
        })
        return stats