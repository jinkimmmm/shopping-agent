# PM2를 사용한 Shopping Agent 실행 가이드

## 📋 개요
PM2(Process Manager 2)를 사용하여 Shopping Agent의 백엔드 API와 프론트엔드 UI를 동시에 관리할 수 있습니다.

## 🚀 빠른 시작

### 1. PM2 설치 (필요한 경우)
```bash
npm install -g pm2
```

### 2. 서비스 시작
```bash
# 방법 1: 스크립트 사용 (권장)
./pm2-commands.sh start

# 방법 2: 직접 PM2 명령 사용
pm2 start ecosystem.config.json
```

### 3. 서비스 상태 확인
```bash
./pm2-commands.sh status
# 또는
pm2 status
```

## 🛠️ 주요 명령어

### 서비스 관리
```bash
# 서비스 시작
./pm2-commands.sh start

# 서비스 중지
./pm2-commands.sh stop

# 서비스 재시작
./pm2-commands.sh restart

# 무중단 리로드 (API만)
./pm2-commands.sh reload

# 서비스 삭제
./pm2-commands.sh delete
```

### 모니터링
```bash
# 상태 확인
./pm2-commands.sh status

# 모든 로그 확인
./pm2-commands.sh logs

# API 로그만 확인
./pm2-commands.sh logs-api

# UI 로그만 확인
./pm2-commands.sh logs-ui

# 실시간 모니터링
./pm2-commands.sh monit
```

## 📊 서비스 구성

### 1. shopping-agent-api
- **포트**: 8001
- **스크립트**: `python3 start_api.py`
- **로그**: `./logs/api.log`, `./logs/api-error.log`
- **URL**: http://localhost:8001

### 2. shopping-agent-ui
- **포트**: 8000
- **스크립트**: `npm start`
- **로그**: `./logs/ui.log`, `./logs/ui-error.log`
- **URL**: http://localhost:8000

## 📁 로그 파일 위치
```
logs/
├── api.log          # API 서버 통합 로그
├── api-error.log    # API 서버 에러 로그
├── api-out.log      # API 서버 출력 로그
├── ui.log           # UI 서버 통합 로그
├── ui-error.log     # UI 서버 에러 로그
└── ui-out.log       # UI 서버 출력 로그
```

## 🔧 설정 파일

### ecosystem.config.json
```json
{
  "apps": [
    {
      "name": "shopping-agent-api",
      "script": "python3",
      "args": "start_api.py",
      "cwd": "/Users/sungjinkim/shopping-agent",
      "interpreter": "none",
      "env": {
        "NODE_ENV": "development",
        "API_HOST": "127.0.0.1",
        "API_PORT": "8001",
        "API_RELOAD": "true",
        "API_LOG_LEVEL": "info"
      },
      "watch": false,
      "autorestart": true,
      "max_restarts": 10,
      "min_uptime": "10s",
      "log_file": "./logs/api.log",
      "error_file": "./logs/api-error.log",
      "out_file": "./logs/api-out.log"
    },
    {
      "name": "shopping-agent-ui",
      "script": "npm",
      "args": "start",
      "cwd": "/Users/sungjinkim/shopping-agent/ui",
      "interpreter": "none",
      "env": {
        "NODE_ENV": "development",
        "PORT": "8000",
        "BROWSER": "none"
      },
      "watch": false,
      "autorestart": true,
      "max_restarts": 10,
      "min_uptime": "10s",
      "log_file": "./logs/ui.log",
      "error_file": "./logs/ui-error.log",
      "out_file": "./logs/ui-out.log"
    }
  ]
}
```

## 🚨 문제 해결

### 1. 포트 충돌
```bash
# 포트 사용 중인 프로세스 확인
lsof -i :8000
lsof -i :8001

# 프로세스 종료
kill -9 <PID>
```

### 2. 서비스가 시작되지 않는 경우
```bash
# 로그 확인
./pm2-commands.sh logs

# 개별 서비스 로그 확인
./pm2-commands.sh logs-api
./pm2-commands.sh logs-ui
```

### 3. PM2 프로세스 완전 정리
```bash
# 모든 PM2 프로세스 삭제
pm2 delete all

# PM2 데몬 종료
pm2 kill
```

## 💡 유용한 팁

### 1. 자동 시작 설정
```bash
# 시스템 부팅 시 자동 시작 설정
pm2 startup
pm2 save
```

### 2. 메모리 사용량 모니터링
```bash
# 실시간 모니터링
pm2 monit

# 메모리 사용량 확인
pm2 list
```

### 3. 로그 로테이션 설정
```bash
# PM2 로그 로테이션 모듈 설치
pm2 install pm2-logrotate

# 로그 로테이션 설정
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 30
```

## 🔗 관련 링크
- [PM2 공식 문서](https://pm2.keymetrics.io/)
- [Shopping Agent API 문서](./api/README.md)
- [프론트엔드 문서](./ui/README.md)

## 📞 지원
문제가 발생하면 다음을 확인해주세요:
1. 로그 파일 (`./logs/` 디렉토리)
2. PM2 상태 (`pm2 status`)
3. 포트 사용 현황 (`lsof -i :8000`, `lsof -i :8001`)