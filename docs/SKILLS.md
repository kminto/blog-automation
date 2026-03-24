# 기술 스킬 패턴

## 1. Streamlit 컴포넌트 작성 패턴

```python
import streamlit as st

# 사이드바 입력 폼
with st.sidebar:
    st.header("입력 정보")
    restaurant_name = st.text_input("음식점 이름")

# 메인 영역 결과 출력
st.subheader("분석 결과")
if st.button("키워드 분석"):
    with st.spinner("분석 중..."):
        result = analyze_keywords(...)
    st.success("완료!")
```

## 2. Anthropic Claude API 호출 패턴

```python
import anthropic
from dotenv import load_dotenv
import os

load_dotenv()

def call_claude(prompt: str, max_tokens: int = 4096) -> str:
    """Claude API를 호출하여 텍스트를 생성한다."""
    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except anthropic.APIConnectionError:
        raise ConnectionError("Claude API 연결에 실패했습니다.")
    except anthropic.RateLimitError:
        raise RuntimeError("Claude API 호출 한도를 초과했습니다.")
    except anthropic.APIStatusError as e:
        raise RuntimeError(f"Claude API 오류: {e.status_code}")
```

## 3. 네이버 키워드도구 API 호출 패턴

```python
import requests
import hashlib
import hmac
import base64
import time

def get_naver_ad_header(api_key: str, secret_key: str, customer_id: str) -> dict:
    """네이버 광고 API 인증 헤더를 생성한다."""
    timestamp = str(int(time.time() * 1000))
    path = "/keywordstool"
    method = "GET"
    sign = f"{timestamp}.{method}.{path}"
    signature = hmac.new(
        secret_key.encode(), sign.encode(), hashlib.sha256
    )
    encoded = base64.b64encode(signature.digest()).decode()
    return {
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key,
        "X-Customer": customer_id,
        "X-Signature": encoded,
    }

def search_keywords(keyword: str) -> list[dict]:
    """네이버 키워드도구에서 키워드 검색량/경쟁도를 조회한다."""
    try:
        url = "https://api.naver.com/keywordstool"
        headers = get_naver_ad_header(...)
        params = {"hintKeywords": keyword, "showDetail": "1"}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("keywordList", [])
    except requests.RequestException as e:
        raise RuntimeError(f"네이버 키워드도구 API 오류: {e}")
```

## 4. 네이버 데이터랩 검색어트렌드 API 호출 패턴

```python
def search_trend(keywords: list[str], start_date: str, end_date: str) -> dict:
    """네이버 데이터랩에서 검색어 트렌드를 조회한다."""
    try:
        url = "https://openapi.naver.com/v1/datalab/search"
        headers = {
            "X-Naver-Client-Id": os.getenv("NAVER_CLIENT_ID"),
            "X-Naver-Client-Secret": os.getenv("NAVER_CLIENT_SECRET"),
            "Content-Type": "application/json",
        }
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": "week",
            "keywordGroups": [
                {"groupName": kw, "keywords": [kw]} for kw in keywords
            ],
        }
        response = requests.post(url, headers=headers, json=body, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"네이버 데이터랩 API 오류: {e}")
```

## 5. .env 환경변수 로드 방식

```python
from dotenv import load_dotenv
import os

load_dotenv()

# 필수 환경변수 검증
REQUIRED_KEYS = [
    "ANTHROPIC_API_KEY",
    "NAVER_CLIENT_ID",
    "NAVER_CLIENT_SECRET",
    "NAVER_AD_API_KEY",
    "NAVER_AD_SECRET_KEY",
    "NAVER_AD_CUSTOMER_ID",
]

def validate_env():
    """필수 환경변수가 모두 설정되어 있는지 확인한다."""
    missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
    if missing:
        raise EnvironmentError(f"환경변수 누락: {', '.join(missing)}")
```

## 6. 에러 처리 공통 패턴

```python
def safe_api_call(func, *args, **kwargs):
    """API 호출을 안전하게 수행하고, 실패 시 사용자 친화적 메시지를 반환한다."""
    try:
        return {"success": True, "data": func(*args, **kwargs)}
    except ConnectionError:
        return {"success": False, "error": "서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."}
    except TimeoutError:
        return {"success": False, "error": "요청 시간이 초과되었습니다."}
    except RuntimeError as e:
        return {"success": False, "error": str(e)}
```

## 7. 말투 생성 랜덤화 패턴

```python
import random

# 매번 다른 구성과 표현을 위한 변주 요소
TONE_VARIATIONS = [
    "친구에게 추천하듯 편안한 말투",
    "일기장에 쓰듯 솔직한 말투",
    "후기 블로그 느낌의 담백한 말투",
]

STRUCTURE_VARIATIONS = [
    "메뉴 소개 → 분위기 → 총평",
    "방문 계기 → 메뉴 → 재방문 의사",
    "분위기 → 메뉴 → 가성비 평가",
]

OPENING_VARIATIONS = [
    "요즘 {지역} 맛집 찾기 정말 어렵지 않나요?",
    "주말에 뭐 먹을지 고민하다가 발견한 곳이에요.",
    "{지역}에서 {메뉴} 맛집 하면 여기를 빼놓을 수 없죠.",
]

def get_random_style() -> dict:
    """매 생성마다 다른 스타일 조합을 반환한다."""
    return {
        "tone": random.choice(TONE_VARIATIONS),
        "structure": random.choice(STRUCTURE_VARIATIONS),
        "opening": random.choice(OPENING_VARIATIONS),
    }
```
