"""
키워드 경쟁도 고도화 모듈
블로그 포화도(총 블로그 수 / 검색량) 기반으로 블루오션 키워드를 발굴한다.
"""

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"


def _get_headers() -> dict:
    """네이버 검색 API 헤더를 반환한다."""
    return {
        "X-Naver-Client-Id": os.getenv("NAVER_CLIENT_ID", ""),
        "X-Naver-Client-Secret": os.getenv("NAVER_CLIENT_SECRET", ""),
    }


def fetch_blog_count(keyword: str) -> int:
    """키워드로 네이버 블로그 검색 결과 총 수를 조회한다."""
    try:
        response = requests.get(
            BLOG_SEARCH_URL,
            headers=_get_headers(),
            params={"query": keyword, "display": 1},
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("total", 0)
    except requests.RequestException:
        return -1


def calc_saturation(blog_count: int, search_volume: int) -> float:
    """블로그 포화도를 계산한다. (낮을수록 블루오션)"""
    if search_volume <= 0:
        return 999.0
    return round(blog_count / search_volume, 2)


def analyze_competition(top_keywords: list[dict], max_check: int = 10) -> list[dict]:
    """상위 키워드의 블로그 포화도를 분석한다."""
    results = []

    for kw_data in top_keywords[:max_check]:
        keyword = kw_data.get("keyword", "")
        search_volume = kw_data.get("search_volume", 0)

        if not keyword:
            continue

        blog_count = fetch_blog_count(keyword)
        if blog_count < 0:
            # API 실패 시 스킵
            results.append({
                **kw_data,
                "blog_count": -1,
                "saturation": -1,
                "opportunity": "미확인",
            })
            continue

        saturation = calc_saturation(blog_count, search_volume)

        # 블루오션 판정
        if saturation < 0.5:
            opportunity = "블루오션"
            bonus = 1.5
        elif saturation < 2.0:
            opportunity = "적정"
            bonus = 1.0
        else:
            opportunity = "레드오션"
            bonus = 0.6

        # 보정 점수 계산
        adjusted_score = round(kw_data.get("score", 0) * bonus, 1)

        results.append({
            **kw_data,
            "blog_count": blog_count,
            "saturation": saturation,
            "opportunity": opportunity,
            "adjusted_score": adjusted_score,
        })

        # API 딜레이 (rate limit 방지)
        time.sleep(0.5)

    # 보정 점수 기준 재정렬
    results.sort(key=lambda x: x.get("adjusted_score", 0), reverse=True)

    return results


def get_blue_ocean_summary(results: list[dict]) -> str:
    """블루오션 분석 결과를 요약한다."""
    blue = [r for r in results if r.get("opportunity") == "블루오션"]
    red = [r for r in results if r.get("opportunity") == "레드오션"]

    lines = []
    if blue:
        kws = ", ".join([r["keyword"] for r in blue[:3]])
        lines.append(f"블루오션 키워드: {kws} (블로그 글 적고 검색량 있음 → 상위 노출 유리)")
    if red:
        kws = ", ".join([r["keyword"] for r in red[:3]])
        lines.append(f"레드오션 주의: {kws} (블로그 글 많아 상위 진입 어려움)")

    if not lines:
        lines.append("모든 키워드가 적정 경쟁 범위입니다.")

    return "\n".join(lines)
