"""
네이버 데이터랩 검색어트렌드 API 모듈
키워드의 검색 추세를 분석하여 상승/유지/하락 여부를 판단한다.
"""

import os
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

from modules.constants import DATALAB_TIME_UNIT, DATALAB_PERIOD_MONTHS

load_dotenv()

DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"


def _get_datalab_headers() -> dict:
    """데이터랩 API 인증 헤더를 반환한다."""
    return {
        "X-Naver-Client-Id": os.getenv("NAVER_CLIENT_ID", ""),
        "X-Naver-Client-Secret": os.getenv("NAVER_CLIENT_SECRET", ""),
        "Content-Type": "application/json",
    }


def fetch_search_trend(keywords: list[str]) -> dict:
    """키워드 목록의 검색 트렌드를 조회한다."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=DATALAB_PERIOD_MONTHS * 30)

    body = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "timeUnit": DATALAB_TIME_UNIT,
        "keywordGroups": [
            {"groupName": kw, "keywords": [kw]}
            for kw in keywords[:5]  # API 제한: 최대 5개 그룹
        ],
    }

    try:
        response = requests.post(
            DATALAB_URL,
            headers=_get_datalab_headers(),
            json=body,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"네이버 데이터랩 API 오류: {e}")


def analyze_trend(trend_data: list[dict]) -> str:
    """트렌드 데이터에서 최근 흐름을 판단한다. (상승/유지/하락)"""
    if not trend_data or len(trend_data) < 4:
        return "유지"

    # 최근 4주 데이터와 이전 4주 데이터 비교
    recent = trend_data[-4:]
    previous = trend_data[-8:-4] if len(trend_data) >= 8 else trend_data[:4]

    recent_avg = sum(d.get("ratio", 0) for d in recent) / len(recent)
    previous_avg = sum(d.get("ratio", 0) for d in previous) / len(previous)

    if previous_avg == 0:
        return "유지"

    change_rate = (recent_avg - previous_avg) / previous_avg

    if change_rate > 0.1:
        return "상승"
    elif change_rate < -0.1:
        return "하락"
    return "유지"
