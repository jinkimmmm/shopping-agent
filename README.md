# Shopping Agent

쇼핑 에이전트 시스템 - AI 기반 자동 쇼핑 도우미

## 프로젝트 개요

Shopping Agent는 사용자의 쇼핑 요청을 자동으로 처리하는 AI 기반 시스템입니다. FastAPI 백엔드와 React 프론트엔드로 구성되어 있으며, 기존 CLI 에이전트 시스템과 통합되어 웹 인터페이스를 제공합니다.

## 기술 스택

### 백엔드 (API)
- **FastAPI**: 고성능 비동기 웹 프레임워크
- **Python 3.11+**: 최신 Python 기능 활용
- **Uvicorn**: ASGI 서버
- **Pydantic**: 데이터 검증 및 직렬화
- **SQLAlchemy**: ORM (계획)

### 프론트엔드 (UI)
- **React 18**: 모던 React 기능 활용
- **TypeScript**: 타입 안전성
- **Material-UI (MUI)**: UI 컴포넌트 라이브러리
- **React Router**: 클라이언트 사이드 라우팅
- **Axios**: HTTP 클라이언트

## 프로젝트 구조

```
shopping-agent/
├── api/                    # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py        # FastAPI 애플리케이션 진입점
│   │   ├── routers/       # API 라우터
│   │   ├── models/        # 데이터 모델
│   │   └── core/          # 핵심 설정
│   ├── requirements.txt   # Python 의존성
│   └── README.md         # API 문서
├── ui/                    # React 프론트엔드
│   ├── src/
│   │   ├── components/    # React 컴포넌트
│   │   ├── pages/         # 페이지 컴포넌트
│   │   └── App.tsx        # 메인 애플리케이션
│   ├── package.json       # Node.js 의존성
│   └── README.md         # UI 문서
├── update/                # 프로젝트 진행 상황
├── task_master.md         # 작업 관리
└── README.md             # 프로젝트 메인 문서
```

## 설치 및 실행

### 백엔드 실행

```bash
# API 디렉토리로 이동
cd api

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate     # Windows

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### 프론트엔드 실행

```bash
# UI 디렉토리로 이동
cd ui

# 의존성 설치
npm install

# 개발 서버 실행
npm start
```

## API 엔드포인트

- `GET /api/health` - 서버 상태 확인
- `GET /api/v1/system/status` - 시스템 상태 조회
- `GET /docs` - Swagger UI 문서
- `GET /redoc` - ReDoc 문서

## 개발 현황

### 완료된 작업 (Phase 1)
- ✅ FastAPI 백엔드 기본 구조
- ✅ React 프론트엔드 기본 구조
- ✅ API 서버 설정 및 CORS 구성
- ✅ 기본 라우팅 및 컴포넌트 구조
- ✅ 모니터링 페이지 구현
- ✅ 기존 시스템과의 통합 준비

### 진행 예정 (Phase 2)
- 🔄 CLI 에이전트와 FastAPI 통합
- 🔄 쇼핑 요청 처리 API 구현
- 🔄 실시간 모니터링 시스템
- 🔄 프론트엔드 핵심 기능 개발

## 라이선스

MIT License

## 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 연락처

프로젝트 관련 문의사항이 있으시면 이슈를 생성해 주세요.