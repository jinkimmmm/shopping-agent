#!/usr/bin/env python3
"""
Shopping Agent API 테스트 스크립트

사용법:
    python test_shopping_api.py

또는 직접 curl 명령어로 테스트:
    curl -X POST "http://localhost:8001/api/v1/requests" \
         -H "Content-Type: application/json" \
         -d '{"query": "Find me the best laptop under $1000", "context": {"budget": 1000, "category": "electronics"}, "user_id": "test_user", "session_id": "test_session"}'
"""

import requests
import json
import time
from typing import Dict, Any, Optional

# API 설정
API_BASE_URL = "http://localhost:8001/api/v1"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def create_shopping_request(query: str, context: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    쇼핑 요청을 생성합니다.
    
    Args:
        query: 자연어 쇼핑 쿼리
        context: 추가 컨텍스트 정보
        user_id: 사용자 ID
        session_id: 세션 ID
    
    Returns:
        API 응답 결과
    """
    url = f"{API_BASE_URL}/requests"
    
    payload = {
        "query": query
    }
    
    if context is not None:
        payload["context"] = context
    if user_id is not None:
        payload["user_id"] = user_id
    if session_id is not None:
        payload["session_id"] = session_id
    
    try:
        print(f"🚀 요청 전송 중...")
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        print("-" * 50)
        
        response = requests.post(url, json=payload, headers=HEADERS)
        
        print(f"📊 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 성공! 요청 ID: {result.get('request_id', 'N/A')}")
            return result
        else:
            print(f"❌ 오류 발생: {response.text}")
            return {"error": response.text, "status_code": response.status_code}
            
    except requests.exceptions.ConnectionError:
        print("❌ 연결 오류: API 서버가 실행 중인지 확인하세요 (http://localhost:8001)")
        return {"error": "Connection failed"}
    except Exception as e:
        print(f"❌ 예외 발생: {str(e)}")
        return {"error": str(e)}

def check_request_status(request_id: str) -> Dict[str, Any]:
    """
    요청 상태를 확인합니다.
    
    Args:
        request_id: 요청 ID
    
    Returns:
        요청 상태 정보
    """
    url = f"{API_BASE_URL}/requests/{request_id}/status"
    
    try:
        response = requests.get(url, headers=HEADERS)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.text, "status_code": response.status_code}
            
    except Exception as e:
        return {"error": str(e)}

def main():
    """
    메인 테스트 함수
    """
    print("🛒 Shopping Agent API 테스트 시작")
    print("=" * 50)
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "노트북 검색",
            "query": "Find me the best laptop under $1000",
            "context": {"budget": 1000, "category": "electronics"},
            "user_id": "test_user_1",
            "session_id": "session_001"
        },
        {
            "name": "스마트폰 검색",
            "query": "최신 아이폰 가격 비교해줘",
            "context": {"category": "mobile", "brand": "apple"},
            "user_id": "test_user_2",
            "session_id": "session_002"
        },
        {
            "name": "간단한 검색",
            "query": "무선 이어폰 추천",
            "user_id": "test_user_3"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 테스트 {i}: {test_case['name']}")
        print("-" * 30)
        
        result = create_shopping_request(
            query=test_case["query"],
            context=test_case.get("context"),
            user_id=test_case.get("user_id"),
            session_id=test_case.get("session_id")
        )
        
        if "request_id" in result:
            print(f"⏳ 잠시 후 상태 확인...")
            time.sleep(2)
            
            status = check_request_status(result["request_id"])
            if "error" not in status:
                print(f"📈 현재 상태: {status.get('status', 'unknown')}")
                print(f"📊 진행률: {status.get('progress', 0) * 100:.1f}%")
                if status.get('current_step'):
                    print(f"🔄 현재 단계: {status['current_step']}")
        
        print("\n" + "=" * 50)
    
    print("\n🎉 테스트 완료!")
    print("\n💡 추가 테스트를 위한 curl 명령어:")
    print(f"curl -X POST \"{API_BASE_URL}/requests\" \\")
    print(f"     -H \"Content-Type: application/json\" \\")
    print(f"     -d '{{\"query\": \"Find me gaming headphones under $200\", \"context\": {{\"budget\": 200, \"category\": \"gaming\"}}, \"user_id\": \"curl_user\"}}'")    

if __name__ == "__main__":
    main()