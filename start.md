


          
사용자가 .env 파일이 없어서 시작할 수 없다고 하니 .env.example 파일을 확인하고 필요한 환경 설정 파일들을 생성해야겠습니다.
        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/sungjinkim/shopping-agent/.env.example
          
맞습니다! 프로젝트를 시작하기 위해서는 환경 설정 파일이 필요합니다. 현재 `.env.example` 파일이 있으니 이를 기반으로 `.env` 파일을 생성하고 필요한 설정을 해보겠습니다.

## 🔧 환경 설정 파일 생성

### 1. .env 파일 생성

먼저 `.env.example`을 복사해서 `.env` 파일을 만들어야 합니다:

```bash
cp .env.example .env
```

### 2. 필수 환경 변수 설정

`.env` 파일에서 다음 항목들을 설정해야 합니다:

#### 🤖 Google Gemini API (필수)
```env
GEMINI_API_KEY=your-actual-gemini-api-key
GEMINI_MODEL=gemini-pro
```

#### 📊 벡터 데이터베이스 (선택)
```env
# Qdrant 사용 시
QDRANT_URL=http://localhost:6333
VECTOR_DB_TYPE=qdrant

# 또는 Chroma 사용 시 (로컬)
CHROMA_PERSIST_DIRECTORY=./data/chroma
VECTOR_DB_TYPE=chroma
```

#### 🗄️ 데이터베이스
```env
DATABASE_URL=sqlite+aiosqlite:///./data/app.db
```

#### 🔐 보안 설정
```env
SECRET_KEY=your-random-secret-key-here
```

### 3. 디렉토리 구조 생성

필요한 데이터 디렉토리들을 생성해야 합니다:

```bash
mkdir -p data/chroma
mkdir -p data/vector_db
mkdir -p logs
```

### 4. 최소 설정으로 시작하기

개발 환경에서 빠르게 시작하려면 다음과 같이 설정하세요:

```env
# 최소 필수 설정
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-pro
VECTOR_DB_TYPE=chroma
CHROMA_PERSIST_DIRECTORY=./data/chroma
DATABASE_URL=sqlite+aiosqlite:///./data/app.db
SECRET_KEY=dev-secret-key-change-in-production
LOG_LEVEL=DEBUG
DEBUG=true
```

### 5. API 키 발급 방법

#### Google Gemini API 키 발급:
1. [Google AI Studio](https://makersuite.google.com/app/apikey) 방문
2. "Create API Key" 클릭
3. 발급받은 키를 `.env` 파일에 설정

### 6. 설치 및 실행

환경 설정 후 다음 명령어로 실행할 수 있습니다:

```bash
# 의존성 설치
pip install -r requirements.txt

# 애플리케이션 실행
python main.py

# 또는 데모 모드로 실행
python main.py --demo
```

### 7. 문제 해결

만약 여전히 문제가 있다면:

1. **Python 가상환경 확인**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   ```

2. **의존성 재설치**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **권한 확인**:
   ```bash
   chmod +x main.py
   ```

이제 환경 설정이 완료되면 쇼핑 에이전트 시스템을 시작할 수 있습니다! 🚀




          
사용자가 현재 쇼핑 에이전트 애플리케이션에서 어떤 인터랙션을 할 수 있는지 궁금해하고 있습니다. 애플리케이션이 성공적으로 초기화되었으므로 main.py 파일을 확인하여 사용 가능한 기능들을 파악해보겠습니다.
        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/sungjinkim/shopping-agent/main.py
          
main.py 파일의 나머지 부분을 확인하여 애플리케이션의 전체 구조와 사용 가능한 기능들을 파악해보겠습니다.
        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/sungjinkim/shopping-agent/main.py
          
main.py의 나머지 부분을 확인하여 사용자 인터랙션 방법과 CLI 인터페이스를 파악해보겠습니다.
        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/sungjinkim/shopping-agent/main.py
          
애플리케이션의 주요 메서드들을 확인하여 사용자가 할 수 있는 인터랙션을 파악해보겠습니다.
        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/sungjinkim/shopping-agent/main.py
          
현재 쇼핑 에이전트 애플리케이션에서 할 수 있는 인터랙션들을 정리해드리겠습니다.

## 🛒 쇼핑 에이전트 시스템 인터랙션 가이드

### 1. 명령줄 인터페이스 (CLI) 옵션

애플리케이션을 다양한 모드로 실행할 수 있습니다:

```bash
# 기본 실행 (대기 모드)
python3 main.py

# 데모 모드 실행
python3 main.py --demo

# 단일 요청 처리
python3 main.py --request "스마트폰 가격 비교해줘"

# 워크플로우 파일 실행
python3 main.py --workflow workflow.json

# 설정 파일 지정
python3 main.py --config config.yaml
```

### 2. 사용 가능한 실행 모드

#### 🎯 데모 모드 (`--demo`)
- 샘플 워크플로우를 자동으로 생성하고 실행
- 상품 정보 수집 및 분석 데모 진행
- 시스템 상태 확인 및 결과 출력

#### 📝 단일 요청 모드 (`--request`)
- 즉시 처리할 요청을 명령줄에서 입력
- 매니저 에이전트가 요청을 분석하고 처리
- JSON 형태로 결과 반환

#### 📋 워크플로우 파일 모드 (`--workflow`)
- JSON 형태의 워크플로우 정의 파일 실행
- 복잡한 다단계 작업 자동화
- 진행 상황 모니터링

#### 🔄 일반 모드 (기본)
- 시스템이 대기 상태로 실행
- 외부 API나 다른 인터페이스를 통한 요청 대기

### 3. 시스템 구성 요소

#### 🤖 에이전트 시스템
- **매니저 에이전트**: 작업 분배 및 조정
- **워커 에이전트들** (5개):
  - 문서 처리 전문 (`document_processing`)
  - 데이터 분석 전문 (`data_analysis`)
  - 고객 서비스 전문 (`customer_service`)
  - 코드 지원 전문 (`code_assistance`)
  - 일반 작업 (`general`)
- **테스터 에이전트**: 결과 검증 및 품질 관리

#### 🔧 도구 시스템
- 웹 스크래핑 도구
- API 클라이언트
- 데이터베이스 도구
- 파일 처리 도구

#### 📊 워크플로우 시스템
- 워크플로우 엔진: 작업 흐름 관리
- 워크플로우 모니터: 실행 상태 추적
- 다단계 작업 자동화

### 4. 예시 사용법

#### 데모 실행
```bash
python3 main.py --demo
```
이 명령으로 시스템의 전체 기능을 체험할 수 있습니다.

#### 간단한 요청 처리
```bash
python3 main.py --request "아이폰 15 최저가 찾아줘"
python3 main.py --request "노트북 추천해줘"
python3 main.py --request "온라인 쇼핑몰 가격 비교"
```

#### 워크플로우 파일 예시
```json
{
  "name": "상품 분석 워크플로우",
  "steps": [
    {
      "id": "collect_data",
      "type": "task",
      "agent_id": "worker_doc_001",
      "config": {
        "task_type": "web_scraping",
        "target_urls": ["https://example-shop.com"]
      }
    }
  ]
}
```

### 5. 시스템 상태 확인

애플리케이션 실행 중에는 다음 정보들을 확인할 수 있습니다:
- 에이전트 상태 (활성/비활성)
- 실행 중인 워크플로우 수
- 등록된 도구 통계
- 시스템 메트릭스

현재 시스템이 성공적으로 초기화되어 있으므로, 위의 어떤 모드로든 실행하여 쇼핑 에이전트의 기능을 활용할 수 있습니다!
        

