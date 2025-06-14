# 쇼핑 에이전트 UI PRD (Product Requirements Document)

## 1. 개요

### 1.1 목적
현재 CLI 기반으로 동작하는 쇼핑 에이전트 시스템에 웹 기반 사용자 인터페이스를 추가하여 사용성을 향상시키고 더 넓은 사용자층에게 서비스를 제공한다.

### 1.2 범위
- FastAPI 기반 백엔드 API 서버 구축
- React/TypeScript 기반 프론트엔드 웹 애플리케이션 개발
- 기존 CLI 기능의 웹 인터페이스 구현
- 실시간 상태 모니터링 및 결과 표시

### 1.3 목표
- 사용자 친화적인 웹 인터페이스 제공
- 실시간 에이전트 작업 상태 모니터링
- 쇼핑 요청 결과의 시각적 표현
- 워크플로우 진행 상황 추적

## 2. 기능 요구사항

### 2.1 핵심 기능

#### 2.1.1 쇼핑 요청 처리
- **기능**: 사용자가 자연어로 쇼핑 요청을 입력
- **입력**: 텍스트 입력 필드
- **출력**: 구조화된 쇼핑 계획 및 결과
- **예시**: "온라인 쇼핑몰 가격 비교", "노트북 추천해줘"

#### 2.1.2 실시간 상태 모니터링
- **기능**: 에이전트 작업 진행 상황 실시간 표시
- **표시 요소**:
  - 현재 실행 중인 에이전트 (Manager, Worker, Tester)
  - 워크플로우 단계별 진행률
  - 각 단계별 소요 시간
  - 에러 발생 시 상세 정보

#### 2.1.3 결과 시각화
- **기능**: 쇼핑 결과를 사용자 친화적으로 표시
- **표시 형태**:
  - 상품 정보 카드
  - 가격 비교 차트
  - 추천 순위 리스트
  - 상세 분석 결과

#### 2.1.4 히스토리 관리 및 데이터 저장
- **기능**: 사용자 질문과 에이전트 답변을 SQLite 데이터베이스에 영구 저장
- **저장 정보**:
  - 사용자 질문 (원본 텍스트)
  - 에이전트 답변 (구조화된 결과)
  - 요청 메타데이터 (타임스탬프, 사용자 ID, 세션 ID)
  - 실행 시간 및 성능 메트릭
  - 워크플로우 실행 로그
  - 성공/실패 상태 및 에러 정보
- **데이터베이스 기능**:
  - 전체 대화 히스토리 검색
  - 날짜/시간 범위별 필터링
  - 키워드 기반 검색
  - 성능 통계 및 분석
  - 데이터 백업 및 복구

### 2.2 부가 기능

#### 2.2.1 설정 관리
- AI 모델 설정 (Gemini 모델 선택)
- 벡터 DB 연결 설정
- 로깅 레벨 조정

#### 2.2.2 시스템 모니터링
- 시스템 상태 대시보드
- 성능 메트릭 표시
- 에러 로그 조회

## 3. 기술 요구사항

### 3.1 백엔드 (FastAPI)

#### 3.1.1 API 엔드포인트
```
POST /api/v1/requests
- 쇼핑 요청 처리
- Request Body: {"query": string, "context": object}
- Response: {"request_id": string, "status": string}

GET /api/v1/requests/{request_id}
- 요청 상태 조회
- Response: {"status": string, "progress": number, "result": object}

GET /api/v1/requests/{request_id}/stream
- 실시간 상태 스트리밍 (WebSocket)

GET /api/v1/health
- 헬스체크
- Response: {"status": "healthy", "timestamp": string}

GET /api/v1/history
- 요청 히스토리 조회
- Query Params: page, limit, search, date_from, date_to
- Response: {"items": array, "total": number, "page": number}

GET /api/v1/conversations
- 전체 대화 히스토리 조회
- Query Params: page, limit, user_id, session_id
- Response: {"conversations": array, "total": number}

GET /api/v1/conversations/{conversation_id}
- 특정 대화 상세 조회
- Response: {"conversation": object, "messages": array}

POST /api/v1/conversations/search
- 키워드 기반 대화 검색
- Request Body: {"keyword": string, "filters": object}
- Response: {"results": array, "total": number}

GET /api/v1/analytics/stats
- 사용 통계 및 성능 분석
- Response: {"total_requests": number, "avg_response_time": number, "success_rate": number}

GET /api/v1/system/status
- 시스템 상태 조회
- Response: {"agents": object, "database": object, "ai_model": object}
```

#### 3.1.2 데이터 모델 (Pydantic)
```python
class ShoppingRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None

class RequestStatus(BaseModel):
    request_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress: float  # 0.0 ~ 1.0
    current_step: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    created_at: datetime
    updated_at: datetime

class ShoppingResult(BaseModel):
    products: List[Product]
    analysis: Dict[str, Any]
    recommendations: List[str]
    execution_time: float

class Product(BaseModel):
    name: str
    price: float
    url: str
    rating: Optional[float]
    reviews: Optional[int]
    image_url: Optional[str]

class Conversation(BaseModel):
    id: int
    user_id: Optional[str]
    session_id: str
    created_at: datetime
    updated_at: datetime
    title: Optional[str]  # 대화 제목 (첫 번째 질문 기반 자동 생성)
    status: Literal["active", "completed", "archived"]

class Message(BaseModel):
    id: int
    conversation_id: int
    message_type: Literal["user_question", "agent_response"]
    content: str  # 사용자 질문 또는 에이전트 응답
    metadata: Optional[Dict[str, Any]]  # 추가 메타데이터
    created_at: datetime
    execution_time: Optional[float]  # 에이전트 응답 시간
    tokens_used: Optional[int]  # AI 모델 토큰 사용량

class ConversationAnalytics(BaseModel):
    conversation_id: int
    total_messages: int
    avg_response_time: float
    total_tokens_used: int
    success_rate: float
    created_at: datetime
```

#### 3.1.3 에러 처리 (RFC 7807)
```python
class ErrorResponse(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
```

#### 3.1.4 CORS 설정
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 개발환경
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 3.1.5 SQLite 데이터베이스 설계

##### 3.1.5.1 테이블 스키마
```sql
-- 대화 세션 테이블
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    session_id TEXT NOT NULL UNIQUE,
    title TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 메시지 테이블 (질문과 답변)
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    message_type TEXT NOT NULL CHECK (message_type IN ('user_question', 'agent_response')),
    content TEXT NOT NULL,
    metadata TEXT, -- JSON 형태로 저장
    execution_time REAL, -- 에이전트 응답 시간 (초)
    tokens_used INTEGER, -- AI 모델 토큰 사용량
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- 요청 상태 추적 테이블
CREATE TABLE request_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL UNIQUE,
    conversation_id INTEGER,
    status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    progress REAL DEFAULT 0.0,
    current_step TEXT,
    error_message TEXT,
    workflow_data TEXT, -- JSON 형태로 워크플로우 실행 로그 저장
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
);

-- 성능 분석 테이블
CREATE TABLE analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    total_messages INTEGER DEFAULT 0,
    avg_response_time REAL DEFAULT 0.0,
    total_tokens_used INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- 인덱스 생성
CREATE INDEX idx_conversations_session_id ON conversations(session_id);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_messages_type ON messages(message_type);
CREATE INDEX idx_request_logs_request_id ON request_logs(request_id);
CREATE INDEX idx_request_logs_status ON request_logs(status);
```

##### 3.1.5.2 데이터베이스 연결 및 ORM 설정
```python
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

Base = declarative_base()

class ConversationDB(Base):
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=True)
    session_id = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=True)
    status = Column(String, default='active')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = relationship("MessageDB", back_populates="conversation", cascade="all, delete-orphan")
    analytics = relationship("AnalyticsDB", back_populates="conversation", cascade="all, delete-orphan")

class MessageDB(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    message_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(Text, nullable=True)  # JSON string
    execution_time = Column(Float, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("ConversationDB", back_populates="messages")
    
    def set_metadata(self, data: dict):
        self.metadata = json.dumps(data) if data else None
    
    def get_metadata(self) -> dict:
        return json.loads(self.metadata) if self.metadata else {}

class RequestLogDB(Base):
    __tablename__ = 'request_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String, nullable=False, unique=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=True)
    status = Column(String, nullable=False)
    progress = Column(Float, default=0.0)
    current_step = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    workflow_data = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AnalyticsDB(Base):
    __tablename__ = 'analytics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    total_messages = Column(Integer, default=0)
    avg_response_time = Column(Float, default=0.0)
    total_tokens_used = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    conversation = relationship("ConversationDB", back_populates="analytics")

# 데이터베이스 설정
DATABASE_URL = "sqlite:///./shopping_agent.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 테이블 생성
Base.metadata.create_all(bind=engine)
```

##### 3.1.5.3 데이터베이스 서비스 클래스
```python
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

class DatabaseService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_conversation(self, user_id: Optional[str], session_id: str, title: Optional[str] = None) -> ConversationDB:
        """새 대화 세션 생성"""
        conversation = ConversationDB(
            user_id=user_id,
            session_id=session_id,
            title=title
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation
    
    def add_message(self, conversation_id: int, message_type: str, content: str, 
                   metadata: Optional[Dict[str, Any]] = None, 
                   execution_time: Optional[float] = None,
                   tokens_used: Optional[int] = None) -> MessageDB:
        """메시지 추가 (사용자 질문 또는 에이전트 응답)"""
        message = MessageDB(
            conversation_id=conversation_id,
            message_type=message_type,
            content=content,
            execution_time=execution_time,
            tokens_used=tokens_used
        )
        if metadata:
            message.set_metadata(metadata)
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        # 분석 데이터 업데이트
        self._update_analytics(conversation_id)
        
        return message
    
    def get_conversation_history(self, conversation_id: int) -> List[MessageDB]:
        """특정 대화의 전체 히스토리 조회"""
        return self.db.query(MessageDB).filter(
            MessageDB.conversation_id == conversation_id
        ).order_by(MessageDB.created_at).all()
    
    def search_conversations(self, keyword: str, user_id: Optional[str] = None, 
                           date_from: Optional[datetime] = None,
                           date_to: Optional[datetime] = None,
                           limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """키워드 기반 대화 검색"""
        query = self.db.query(MessageDB).join(ConversationDB)
        
        # 키워드 검색
        query = query.filter(MessageDB.content.contains(keyword))
        
        # 필터 적용
        if user_id:
            query = query.filter(ConversationDB.user_id == user_id)
        if date_from:
            query = query.filter(MessageDB.created_at >= date_from)
        if date_to:
            query = query.filter(MessageDB.created_at <= date_to)
        
        messages = query.order_by(MessageDB.created_at.desc()).offset(offset).limit(limit).all()
        
        # 결과 포맷팅
        results = []
        for message in messages:
            results.append({
                'conversation_id': message.conversation_id,
                'message_id': message.id,
                'message_type': message.message_type,
                'content': message.content[:200] + '...' if len(message.content) > 200 else message.content,
                'created_at': message.created_at,
                'conversation_title': message.conversation.title
            })
        
        return results
    
    def get_analytics(self, conversation_id: Optional[int] = None, 
                     date_from: Optional[datetime] = None,
                     date_to: Optional[datetime] = None) -> Dict[str, Any]:
        """사용 통계 및 분석 데이터 조회"""
        query = self.db.query(AnalyticsDB)
        
        if conversation_id:
            query = query.filter(AnalyticsDB.conversation_id == conversation_id)
        if date_from:
            query = query.filter(AnalyticsDB.created_at >= date_from)
        if date_to:
            query = query.filter(AnalyticsDB.created_at <= date_to)
        
        analytics = query.all()
        
        if not analytics:
            return {
                'total_conversations': 0,
                'total_messages': 0,
                'avg_response_time': 0.0,
                'total_tokens_used': 0,
                'avg_success_rate': 0.0
            }
        
        return {
            'total_conversations': len(analytics),
            'total_messages': sum(a.total_messages for a in analytics),
            'avg_response_time': sum(a.avg_response_time for a in analytics) / len(analytics),
            'total_tokens_used': sum(a.total_tokens_used for a in analytics),
            'avg_success_rate': sum(a.success_rate for a in analytics) / len(analytics)
        }
    
    def _update_analytics(self, conversation_id: int):
        """대화 분석 데이터 업데이트"""
        messages = self.get_conversation_history(conversation_id)
        
        # 응답 메시지만 필터링
        response_messages = [m for m in messages if m.message_type == 'agent_response']
        
        if not response_messages:
            return
        
        # 분석 데이터 계산
        total_messages = len(messages)
        avg_response_time = sum(m.execution_time or 0 for m in response_messages) / len(response_messages)
        total_tokens_used = sum(m.tokens_used or 0 for m in response_messages)
        success_rate = len([m for m in response_messages if m.execution_time is not None]) / len(response_messages)
        
        # 기존 분석 데이터 업데이트 또는 생성
        analytics = self.db.query(AnalyticsDB).filter(
            AnalyticsDB.conversation_id == conversation_id
        ).first()
        
        if analytics:
            analytics.total_messages = total_messages
            analytics.avg_response_time = avg_response_time
            analytics.total_tokens_used = total_tokens_used
            analytics.success_rate = success_rate
            analytics.updated_at = datetime.utcnow()
        else:
            analytics = AnalyticsDB(
                conversation_id=conversation_id,
                total_messages=total_messages,
                avg_response_time=avg_response_time,
                total_tokens_used=total_tokens_used,
                success_rate=success_rate
            )
            self.db.add(analytics)
        
        self.db.commit()
```

### 3.2 프론트엔드 (React + TypeScript)

#### 3.2.1 프로젝트 구조 (기존 에이전트 시스템 유지)
```
shopping-agent/
├── agents/              # 기존 에이전트 시스템 (유지)
├── ai/                  # AI 관련 모듈 (유지)
├── core/                # 핵심 설정 및 로깅 (유지)
├── tools/               # 도구 관리자 (유지)
├── workflow/            # 워크플로우 엔진 (유지)
├── main.py              # 기존 CLI 애플리케이션 (유지)
├── api/                 # 새로 추가: FastAPI 서버
│   ├── __init__.py
│   ├── main.py          # FastAPI 애플리케이션
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── requests.py  # 쇼핑 요청 API
│   │   ├── history.py   # 히스토리 API
│   │   └── system.py    # 시스템 상태 API
│   ├── models/
│   │   ├── __init__.py
│   │   ├── request.py   # Pydantic 모델
│   │   └── response.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── agent_service.py  # 기존 에이전트 연동
│   │   └── database_service.py
│   └── database/
│       ├── __init__.py
│       ├── models.py    # SQLAlchemy 모델
│       └── connection.py
└── ui/                  # React 웹 애플리케이션
    ├── public/
    │   ├── index.html
    │   └── favicon.ico
    ├── src/
    │   ├── components/
    │   │   ├── common/
    │   │   │   ├── Header.tsx
    │   │   │   ├── Sidebar.tsx
    │   │   │   ├── LoadingSpinner.tsx
    │   │   │   └── ErrorBoundary.tsx
    │   │   ├── request/
    │   │   │   ├── RequestForm.tsx
    │   │   │   ├── RequestStatus.tsx
    │   │   │   └── ProgressBar.tsx
    │   │   ├── results/
    │   │   │   ├── ResultsView.tsx
    │   │   │   ├── ProductCard.tsx
    │   │   │   ├── PriceChart.tsx
    │   │   │   └── RecommendationList.tsx
    │   │   └── history/
    │   │       ├── HistoryList.tsx
    │   │       └── HistoryItem.tsx
    │   ├── pages/
    │   │   ├── HomePage.tsx
    │   │   ├── HistoryPage.tsx
    │   │   └── SettingsPage.tsx
    │   ├── hooks/
    │   │   ├── useShoppingRequest.ts
    │   │   ├── useWebSocket.ts
    │   │   └── useHistory.ts
    │   ├── services/
    │   │   ├── api.ts
    │   │   └── websocket.ts
    │   ├── types/
    │   │   └── index.ts
    │   ├── utils/
    │   │   ├── formatters.ts
    │   │   └── validators.ts
    │   ├── App.tsx
    │   └── index.tsx
    ├── package.json
    ├── tsconfig.json
    └── .env.local
```

#### 3.2.2 구현 전략

**A. 기존 시스템 보존**
- 현재 CLI 기반 에이전트 시스템은 그대로 유지
- `main.py`와 모든 기존 모듈들 변경 없음

**B. API 서버 추가**
- `api/` 폴더에 FastAPI 서버 구축
- 기존 `ShoppingAgentApp` 클래스를 import해서 사용
- 기존 에이전트들을 웹 API로 노출

**C. UI 개발**
- `ui/` 폴더에 독립적인 React 애플리케이션
- `api/` 서버와 HTTP/WebSocket 통신
- 별도의 빌드 프로세스

#### 3.2.2 주요 인터페이스
```typescript
interface ShoppingRequest {
  query: string;
  context?: Record<string, any>;
}

interface RequestStatus {
  requestId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  currentStep?: string;
  result?: ShoppingResult;
  error?: string;
  createdAt: string;
  updatedAt: string;
}

interface ShoppingResult {
  products: Product[];
  analysis: Record<string, any>;
  recommendations: string[];
  executionTime: number;
}

interface Product {
  name: string;
  price: number;
  url: string;
  rating?: number;
  reviews?: number;
  imageUrl?: string;
}
```

#### 3.2.3 상태 관리 (React Query + Zustand)
```typescript
// API 상태 관리
const useShoppingRequest = () => {
  return useMutation({
    mutationFn: (request: ShoppingRequest) => 
      api.post('/requests', request),
    onSuccess: (data) => {
      // WebSocket 연결 시작
    }
  });
};

// 전역 상태 관리
interface AppState {
  currentRequest: RequestStatus | null;
  history: RequestStatus[];
  setCurrentRequest: (request: RequestStatus) => void;
  addToHistory: (request: RequestStatus) => void;
}
```

## 4. UI/UX 설계

### 4.1 레이아웃

#### 4.1.1 메인 페이지
```
┌─────────────────────────────────────────┐
│ Header (로고, 네비게이션, 설정)              │
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │ 요청 입력 폼                          │ │
│ │ [텍스트 입력 필드]        [전송 버튼] │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ 진행 상황 표시                        │ │
│ │ [진행률 바] [현재 단계] [소요시간]    │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ 결과 표시 영역                        │ │
│ │ [상품 카드들] [차트] [추천 리스트]    │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

#### 4.1.2 히스토리 페이지
```
┌─────────────────────────────────────────┐
│ Header                                  │
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │ 필터 및 검색                          │ │
│ │ [날짜 범위] [상태] [검색어]           │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ 히스토리 리스트                       │ │
│ │ ┌─────────────────────────────────┐ │ │
│ │ │ 요청 항목 1                     │ │ │
│ │ │ [시간] [요청] [상태] [결과보기]  │ │ │
│ │ └─────────────────────────────────┘ │ │
│ │ ┌─────────────────────────────────┐ │ │
│ │ │ 요청 항목 2                     │ │ │
│ │ └─────────────────────────────────┘ │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 4.2 컴포넌트 상세

#### 4.2.1 RequestForm 컴포넌트
```typescript
interface RequestFormProps {
  onSubmit: (request: ShoppingRequest) => void;
  isLoading: boolean;
}

const RequestForm: React.FC<RequestFormProps> = ({ onSubmit, isLoading }) => {
  const [query, setQuery] = useState('');
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSubmit({ query: query.trim() });
    }
  };
  
  return (
    <form onSubmit={handleSubmit} className="request-form">
      <div className="input-group">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="쇼핑 요청을 입력하세요 (예: 노트북 추천해줘)"
          className="query-input"
          rows={3}
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={!query.trim() || isLoading}
          className="submit-button"
        >
          {isLoading ? <LoadingSpinner /> : '요청 전송'}
        </button>
      </div>
    </form>
  );
};
```

#### 4.2.2 ProgressBar 컴포넌트
```typescript
interface ProgressBarProps {
  progress: number; // 0-1
  currentStep?: string;
  estimatedTime?: number;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ 
  progress, 
  currentStep, 
  estimatedTime 
}) => {
  return (
    <div className="progress-container">
      <div className="progress-info">
        <span className="current-step">{currentStep || '대기 중...'}</span>
        <span className="progress-percent">{Math.round(progress * 100)}%</span>
      </div>
      <div className="progress-bar">
        <div 
          className="progress-fill" 
          style={{ width: `${progress * 100}%` }}
        />
      </div>
      {estimatedTime && (
        <div className="estimated-time">
          예상 완료 시간: {estimatedTime}초
        </div>
      )}
    </div>
  );
};
```

#### 4.2.3 ProductCard 컴포넌트
```typescript
interface ProductCardProps {
  product: Product;
  onClick?: () => void;
}

const ProductCard: React.FC<ProductCardProps> = ({ product, onClick }) => {
  return (
    <div className="product-card" onClick={onClick}>
      {product.imageUrl && (
        <img 
          src={product.imageUrl} 
          alt={product.name}
          className="product-image"
        />
      )}
      <div className="product-info">
        <h3 className="product-name">{product.name}</h3>
        <div className="product-price">
          {product.price.toLocaleString()}원
        </div>
        {product.rating && (
          <div className="product-rating">
            ⭐ {product.rating} ({product.reviews}개 리뷰)
          </div>
        )}
        <a 
          href={product.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="product-link"
          onClick={(e) => e.stopPropagation()}
        >
          상품 보기
        </a>
      </div>
    </div>
  );
};
```

## 5. 개발 계획

### 5.1 Phase 1: 기본 구조 (1주)
- [ ] FastAPI 서버 기본 구조 설정
- [ ] React 프로젝트 초기화
- [ ] 기본 API 엔드포인트 구현
- [ ] 메인 페이지 레이아웃 구현

### 5.2 Phase 2: 핵심 기능 (1주)
- [ ] 쇼핑 요청 처리 API 구현
- [ ] 실시간 상태 업데이트 (WebSocket)
- [ ] 결과 표시 컴포넌트 구현
- [ ] 에러 처리 및 로딩 상태

### 5.3 Phase 3: 부가 기능 (0.5주)
- [ ] 히스토리 관리
- [ ] 설정 페이지
- [ ] 시스템 모니터링
- [ ] 성능 최적화

### 5.4 Phase 4: 테스트 및 배포 (0.5주)
- [ ] 단위 테스트 작성
- [ ] E2E 테스트
- [ ] 배포 설정
- [ ] 문서화

## 6. 성능 요구사항

### 6.1 응답 시간
- API 응답 시간: < 200ms (단순 조회)
- 쇼핑 요청 처리: < 30초
- 페이지 로딩 시간: < 2초

### 6.2 동시 사용자
- 최대 동시 사용자: 100명
- 동시 쇼핑 요청 처리: 10개

### 6.3 가용성
- 서비스 가용성: 99.9%
- 에러율: < 1%

## 7. 보안 요구사항

### 7.1 인증/인가
- 현재는 인증 없이 구현 (추후 JWT 토큰 기반 인증 추가 예정)
- API 키 기반 외부 서비스 접근 제어

### 7.2 데이터 보호
- 사용자 입력 데이터 검증
- XSS, CSRF 공격 방지
- 민감 정보 로깅 금지

### 7.3 네트워크 보안
- HTTPS 사용 (프로덕션)
- CORS 정책 적용
- Rate Limiting

## 8. 모니터링 및 로깅

### 8.1 로깅
- 구조화된 로그 (JSON 형태)
- 로그 레벨: DEBUG, INFO, WARNING, ERROR
- 요청/응답 로깅
- 성능 메트릭 로깅

### 8.2 모니터링
- 시스템 리소스 모니터링
- API 응답 시간 모니터링
- 에러율 모니터링
- 사용자 행동 분석

## 9. 배포 및 운영

### 9.1 개발 환경
- 로컬 개발: Docker Compose
- 백엔드: uvicorn --reload
- 프론트엔드: npm run dev

### 9.2 프로덕션 환경
- 컨테이너 기반 배포 (Docker)
- 리버스 프록시 (Nginx)
- 프로세스 관리 (PM2 또는 systemd)

### 9.3 CI/CD
- GitHub Actions
- 자동 테스트 실행
- 자동 배포 (스테이징 → 프로덕션)

## 10. 향후 개선사항

### 10.1 단기 (1-2개월)
- 사용자 인증 시스템
- 개인화된 추천
- 모바일 반응형 디자인
- 다국어 지원

### 10.2 중기 (3-6개월)
- 실시간 알림 시스템
- 고급 필터링 및 정렬
- 데이터 분석 대시보드
- API 버전 관리

### 10.3 장기 (6개월 이상)
- 마이크로서비스 아키텍처 전환
- 머신러닝 기반 개인화
- 모바일 앱 개발
- 써드파티 통합 확장