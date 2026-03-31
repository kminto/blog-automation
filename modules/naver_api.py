"""
네이버 키워드도구 API 모듈
네이버 검색광고 API를 통해 키워드 검색량과 경쟁도를 조회한다.
"""

import hashlib
import hmac
import base64
import time
import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.searchad.naver.com"
KEYWORD_TOOL_PATH = "/keywordstool"


def _create_signature(timestamp: str, method: str, path: str) -> str:
    """HMAC-SHA256 서명을 생성한다."""
    secret_key = os.getenv("NAVER_AD_SECRET_KEY", "")
    sign = f"{timestamp}.{method}.{path}"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        sign.encode("utf-8"),
        hashlib.sha256,
    )
    return base64.b64encode(signature.digest()).decode("utf-8")


def _get_auth_headers(method: str, path: str) -> dict:
    """네이버 광고 API 인증 헤더를 생성한다."""
    timestamp = str(int(time.time() * 1000))
    return {
        "X-Timestamp": timestamp,
        "X-API-KEY": os.getenv("NAVER_AD_API_KEY", ""),
        "X-Customer": os.getenv("NAVER_AD_CUSTOMER_ID", ""),
        "X-Signature": _create_signature(timestamp, method, path),
    }


def fetch_keyword_stats(keywords: list[str]) -> list[dict]:
    """키워드 목록의 검색량과 경쟁도를 조회한다."""
    headers = _get_auth_headers("GET", KEYWORD_TOOL_PATH)
    # 네이버 키워드도구는 공백 없이 붙여서 보내야 정확한 결과
    cleaned = [kw.replace(" ", "") for kw in keywords[:5]]
    hint = ",".join(cleaned)

    params = {
        "hintKeywords": hint,
        "showDetail": "1",
    }

    try:
        response = requests.get(
            f"{BASE_URL}{KEYWORD_TOOL_PATH}",
            headers=headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("keywordList", [])
    except requests.RequestException as e:
        raise RuntimeError(f"네이버 키워드도구 API 오류: {e}")


def fetch_keyword_stats_batch(keywords: list[str]) -> list[dict]:
    """키워드를 5개씩 나눠서 배치 조회한다. 레이트 리밋 방지를 위해 딜레이 포함."""
    all_results = []
    batches = [keywords[i:i + 5] for i in range(0, len(keywords), 5)]

    for idx, batch in enumerate(batches):
        # 두 번째 배치부터 1.0초 대기 (429 시 자동 재시도)
        if idx > 0:
            time.sleep(1.0)

        try:
            results = fetch_keyword_stats(batch)
            all_results.extend(results)
        except RuntimeError as e:
            # 429 에러 시 3초 대기 후 재시도
            if "429" in str(e):
                time.sleep(3)
                try:
                    results = fetch_keyword_stats(batch)
                    all_results.extend(results)
                except RuntimeError:
                    continue  # 재시도 실패 시 해당 배치 건너뜀
            else:
                raise

    return all_results
