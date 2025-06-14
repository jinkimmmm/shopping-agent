#!/bin/bash

# PM2 Shopping Agent 관리 스크립트

case "$1" in
  start)
    echo "🚀 Shopping Agent 서비스 시작 중..."
    # 로그 디렉토리 생성
    mkdir -p logs
    # PM2로 서비스 시작
    pm2 start ecosystem.config.json
    echo "✅ 서비스가 시작되었습니다."
    echo "📊 상태 확인: pm2 status"
    echo "📋 로그 확인: pm2 logs"
    echo "🌐 프론트엔드: http://localhost:8000"
    echo "🔧 API: http://localhost:8001"
    ;;
  stop)
    echo "⏹️  Shopping Agent 서비스 중지 중..."
    pm2 stop ecosystem.config.js
    echo "✅ 서비스가 중지되었습니다."
    ;;
  restart)
    echo "🔄 Shopping Agent 서비스 재시작 중..."
    pm2 restart ecosystem.config.js
    echo "✅ 서비스가 재시작되었습니다."
    ;;
  reload)
    echo "🔄 Shopping Agent 서비스 리로드 중..."
    pm2 reload ecosystem.config.js
    echo "✅ 서비스가 리로드되었습니다."
    ;;
  delete)
    echo "🗑️  Shopping Agent 서비스 삭제 중..."
    pm2 delete ecosystem.config.js
    echo "✅ 서비스가 삭제되었습니다."
    ;;
  status)
    echo "📊 Shopping Agent 서비스 상태:"
    pm2 status
    ;;
  logs)
    echo "📋 Shopping Agent 로그:"
    pm2 logs
    ;;
  logs-api)
    echo "📋 API 서버 로그:"
    pm2 logs shopping-agent-api
    ;;
  logs-ui)
    echo "📋 UI 서버 로그:"
    pm2 logs shopping-agent-ui
    ;;
  monit)
    echo "📈 PM2 모니터링 시작:"
    pm2 monit
    ;;
  *)
    echo "🛒 Shopping Agent PM2 관리 스크립트"
    echo ""
    echo "사용법: $0 {start|stop|restart|reload|delete|status|logs|logs-api|logs-ui|monit}"
    echo ""
    echo "명령어:"
    echo "  start     - 백엔드와 프론트엔드 서비스 시작"
    echo "  stop      - 모든 서비스 중지"
    echo "  restart   - 모든 서비스 재시작"
    echo "  reload    - 무중단 리로드 (API만 해당)"
    echo "  delete    - PM2에서 서비스 삭제"
    echo "  status    - 서비스 상태 확인"
    echo "  logs      - 모든 로그 확인"
    echo "  logs-api  - API 서버 로그만 확인"
    echo "  logs-ui   - UI 서버 로그만 확인"
    echo "  monit     - PM2 모니터링 대시보드"
    echo ""
    echo "예시:"
    echo "  $0 start    # 서비스 시작"
    echo "  $0 logs     # 로그 확인"
    echo "  $0 status   # 상태 확인"
    exit 1
    ;;
esac