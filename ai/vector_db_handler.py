"""벡터 데이터베이스 핸들러"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from qdrant_client.http.models import Distance, VectorParams
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

from .gemini_client import GeminiClient
from core.config import get_config
from core.logger import LoggerMixin, log_function_call


@dataclass
class Document:
    """문서 데이터 클래스"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class SearchResult:
    """검색 결과 데이터 클래스"""
    document: Document
    score: float
    rank: int


@dataclass
class SearchQuery:
    """검색 쿼리 데이터 클래스"""
    text: str
    embedding: Optional[List[float]] = None
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10
    threshold: float = 0.7


class VectorDBHandler(LoggerMixin):
    """벡터 데이터베이스 핸들러"""
    
    def __init__(self, gemini_client: GeminiClient, db_type: str = "chroma"):
        """핸들러 초기화"""
        self.gemini_client = gemini_client
        self.settings = get_config()
        self.db_type = db_type.lower()
        
        # 데이터베이스 클라이언트 초기화
        self.client = None
        self.collection = None
        
        # 임베딩 캐시
        self.embedding_cache = {}
        
        # 초기화
        asyncio.create_task(self._initialize_db())
    
    async def _initialize_db(self):
        """데이터베이스 초기화"""
        try:
            if self.db_type == "chroma":
                await self._initialize_chroma()
            elif self.db_type == "qdrant":
                await self._initialize_qdrant()
            else:
                raise ValueError(f"지원하지 않는 데이터베이스 유형: {self.db_type}")
            
            self.logger.info(f"{self.db_type} 데이터베이스 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"데이터베이스 초기화 실패: {e}")
            raise
    
    async def _initialize_chroma(self):
        """ChromaDB 초기화"""
        if not CHROMA_AVAILABLE:
            raise ImportError("ChromaDB가 설치되지 않았습니다. pip install chromadb")
        
        # ChromaDB 클라이언트 생성
        if self.settings.chroma_host and self.settings.chroma_port:
            # 원격 ChromaDB
            self.client = chromadb.HttpClient(
                host=self.settings.chroma_host,
                port=self.settings.chroma_port
            )
        else:
            # 로컬 ChromaDB
            self.client = chromadb.PersistentClient(
                path=self.settings.chroma_persist_directory or "./data/chroma"
            )
        
        # 컬렉션 생성 또는 가져오기
        collection_name = self.settings.chroma_collection_name or "agent_documents"
        try:
            self.collection = self.client.get_collection(name=collection_name)
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Agent documents collection"}
            )
    
    async def _initialize_qdrant(self):
        """Qdrant 초기화"""
        if not QDRANT_AVAILABLE:
            raise ImportError("Qdrant 클라이언트가 설치되지 않았습니다. pip install qdrant-client")
        
        # Qdrant 클라이언트 생성
        if self.settings.qdrant_url:
            self.client = QdrantClient(
                url=self.settings.qdrant_url,
                api_key=self.settings.qdrant_api_key
            )
        else:
            self.client = QdrantClient(":memory:")  # 메모리 모드
        
        # 컬렉션 생성
        collection_name = self.settings.qdrant_collection_name or "agent_documents"
        
        try:
            # 컬렉션 존재 확인
            collections = await self.client.get_collections()
            collection_exists = any(
                col.name == collection_name for col in collections.collections
            )
            
            if not collection_exists:
                # 컬렉션 생성
                await self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=768,  # Gemini 임베딩 차원
                        distance=Distance.COSINE
                    )
                )
            
            self.collection_name = collection_name
            
        except Exception as e:
            self.logger.warning(f"Qdrant 컬렉션 설정 중 오류: {e}")
    
    @log_function_call
    async def generate_embedding(self, text: str) -> List[float]:
        """텍스트 임베딩 생성"""
        # 캐시 확인
        if text in self.embedding_cache:
            return self.embedding_cache[text]
        
        try:
            # Gemini를 사용한 임베딩 생성
            # 실제로는 Gemini의 임베딩 API를 사용해야 하지만,
            # 여기서는 텍스트 생성 API를 사용한 시뮬레이션
            
            # 간단한 해시 기반 임베딩 (실제 구현에서는 실제 임베딩 API 사용)
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()
            
            # 768차원 벡터 생성 (Gemini 임베딩 차원)
            embedding = []
            for i in range(768):
                # 해시를 기반으로 한 의사 임베딩
                seed = int(text_hash[i % len(text_hash)], 16) + i
                np.random.seed(seed)
                embedding.append(float(np.random.normal(0, 1)))
            
            # 정규화
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = [x / norm for x in embedding]
            
            # 캐시에 저장
            self.embedding_cache[text] = embedding
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"임베딩 생성 실패: {e}")
            # 기본 임베딩 반환
            return [0.0] * 768
    
    @log_function_call
    async def add_document(self, document: Document) -> bool:
        """문서 추가"""
        try:
            # 임베딩 생성
            if document.embedding is None:
                document.embedding = await self.generate_embedding(document.content)
            
            if self.db_type == "chroma":
                return await self._add_document_chroma(document)
            elif self.db_type == "qdrant":
                return await self._add_document_qdrant(document)
            
        except Exception as e:
            self.logger.error(f"문서 추가 실패: {e}")
            return False
    
    async def _add_document_chroma(self, document: Document) -> bool:
        """ChromaDB에 문서 추가"""
        try:
            self.collection.add(
                ids=[document.id],
                embeddings=[document.embedding],
                documents=[document.content],
                metadatas=[document.metadata]
            )
            return True
        except Exception as e:
            self.logger.error(f"ChromaDB 문서 추가 실패: {e}")
            return False
    
    async def _add_document_qdrant(self, document: Document) -> bool:
        """Qdrant에 문서 추가"""
        try:
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=document.id,
                        vector=document.embedding,
                        payload={
                            "content": document.content,
                            "metadata": document.metadata,
                            "created_at": document.created_at.isoformat(),
                            "updated_at": document.updated_at.isoformat()
                        }
                    )
                ]
            )
            return True
        except Exception as e:
            self.logger.error(f"Qdrant 문서 추가 실패: {e}")
            return False
    
    @log_function_call
    async def search_documents(
        self,
        query: SearchQuery
    ) -> List[SearchResult]:
        """문서 검색"""
        try:
            # 쿼리 임베딩 생성
            if query.embedding is None:
                query.embedding = await self.generate_embedding(query.text)
            
            if self.db_type == "chroma":
                return await self._search_documents_chroma(query)
            elif self.db_type == "qdrant":
                return await self._search_documents_qdrant(query)
            
            return []
            
        except Exception as e:
            self.logger.error(f"문서 검색 실패: {e}")
            return []
    
    async def _search_documents_chroma(self, query: SearchQuery) -> List[SearchResult]:
        """ChromaDB에서 문서 검색"""
        try:
            # 검색 실행
            results = self.collection.query(
                query_embeddings=[query.embedding],
                n_results=query.limit,
                where=query.filters
            )
            
            # 결과 변환
            search_results = []
            for i, (doc_id, content, metadata, distance) in enumerate(zip(
                results['ids'][0],
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                # 거리를 유사도로 변환 (1 - distance)
                score = 1.0 - distance
                
                if score >= query.threshold:
                    document = Document(
                        id=doc_id,
                        content=content,
                        metadata=metadata
                    )
                    
                    search_results.append(SearchResult(
                        document=document,
                        score=score,
                        rank=i + 1
                    ))
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"ChromaDB 검색 실패: {e}")
            return []
    
    async def _search_documents_qdrant(self, query: SearchQuery) -> List[SearchResult]:
        """Qdrant에서 문서 검색"""
        try:
            # 필터 변환
            qdrant_filter = None
            if query.filters:
                # Qdrant 필터 형식으로 변환
                qdrant_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key=f"metadata.{key}",
                            match=models.MatchValue(value=value)
                        )
                        for key, value in query.filters.items()
                    ]
                )
            
            # 검색 실행
            results = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query.embedding,
                query_filter=qdrant_filter,
                limit=query.limit,
                score_threshold=query.threshold
            )
            
            # 결과 변환
            search_results = []
            for i, result in enumerate(results):
                document = Document(
                    id=str(result.id),
                    content=result.payload["content"],
                    metadata=result.payload["metadata"]
                )
                
                search_results.append(SearchResult(
                    document=document,
                    score=result.score,
                    rank=i + 1
                ))
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"Qdrant 검색 실패: {e}")
            return []
    
    @log_function_call
    async def update_document(self, document: Document) -> bool:
        """문서 업데이트"""
        try:
            document.updated_at = datetime.now()
            
            # 임베딩 재생성
            document.embedding = await self.generate_embedding(document.content)
            
            # 문서 추가 (upsert)
            return await self.add_document(document)
            
        except Exception as e:
            self.logger.error(f"문서 업데이트 실패: {e}")
            return False
    
    @log_function_call
    async def delete_document(self, document_id: str) -> bool:
        """문서 삭제"""
        try:
            if self.db_type == "chroma":
                self.collection.delete(ids=[document_id])
                return True
            elif self.db_type == "qdrant":
                await self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(
                        points=[document_id]
                    )
                )
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"문서 삭제 실패: {e}")
            return False
    
    @log_function_call
    async def get_document(self, document_id: str) -> Optional[Document]:
        """문서 조회"""
        try:
            if self.db_type == "chroma":
                results = self.collection.get(
                    ids=[document_id],
                    include=["documents", "metadatas"]
                )
                
                if results['ids']:
                    return Document(
                        id=results['ids'][0],
                        content=results['documents'][0],
                        metadata=results['metadatas'][0]
                    )
            
            elif self.db_type == "qdrant":
                result = await self.client.retrieve(
                    collection_name=self.collection_name,
                    ids=[document_id]
                )
                
                if result:
                    point = result[0]
                    return Document(
                        id=str(point.id),
                        content=point.payload["content"],
                        metadata=point.payload["metadata"]
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"문서 조회 실패: {e}")
            return None
    
    @log_function_call
    async def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 조회"""
        try:
            if self.db_type == "chroma":
                count = self.collection.count()
                return {
                    "total_documents": count,
                    "collection_name": self.collection.name,
                    "database_type": "chroma"
                }
            
            elif self.db_type == "qdrant":
                info = await self.client.get_collection(self.collection_name)
                return {
                    "total_documents": info.points_count,
                    "collection_name": self.collection_name,
                    "database_type": "qdrant",
                    "vector_size": info.config.params.vectors.size,
                    "distance_metric": info.config.params.vectors.distance.value
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"컬렉션 통계 조회 실패: {e}")
            return {}
    
    @log_function_call
    async def batch_add_documents(self, documents: List[Document]) -> Dict[str, int]:
        """문서 배치 추가"""
        success_count = 0
        failed_count = 0
        
        for document in documents:
            if await self.add_document(document):
                success_count += 1
            else:
                failed_count += 1
        
        self.logger.info(
            "배치 문서 추가 완료",
            extra={
                "success_count": success_count,
                "failed_count": failed_count,
                "total_count": len(documents)
            }
        )
        
        return {
            "success": success_count,
            "failed": failed_count,
            "total": len(documents)
        }
    
    async def close(self):
        """연결 종료"""
        try:
            if self.db_type == "qdrant" and self.client:
                await self.client.close()
            
            self.logger.info("벡터 데이터베이스 연결 종료")
            
        except Exception as e:
            self.logger.error(f"연결 종료 실패: {e}")