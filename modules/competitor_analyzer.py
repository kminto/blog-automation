"""
경쟁 블로그 분석기 모듈
네이버 블로그 검색 API로 상위 글을 분석하여
내 글의 경쟁력을 평가하고 개선 가이드를 제공한다.
"""

import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"


def _get_search_headers() -> dict:
    """네이버 검색 API 인증 헤더를 반환한다."""
    return {
        "X-Naver-Client-Id": os.getenv("NAVER_CLIENT_ID", ""),
        "X-Naver-Client-Secret": os.getenv("NAVER_CLIENT_SECRET", ""),
    }


def _strip_html(text: str) -> str:
    """HTML 태그를 제거한다."""
    return re.sub(r"<[^>]+>", "", text)


def analyze_top_posts(keyword: str, count: int = 5) -> list[dict]:
    """네이버 블로그 검색 API로 키워드 상위 글을 분석한다.

    Args:
        keyword: 검색 키워드
        count: 분석할 글 수 (기본 5)

    Returns:
        [{"title": str, "desc_length": int, "link": str}, ...]
    """
    try:
        response = requests.get(
            BLOG_SEARCH_URL,
            headers=_get_search_headers(),
            params={"query": keyword, "display": count, "sort": "sim"},
            timeout=10,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    except requests.RequestException:
        return []

    results = []
    for item in items:
        title = _strip_html(item.get("title", ""))
        description = _strip_html(item.get("description", ""))
        link = item.get("link", "")

        results.append({
            "title": title,
            "desc_length": len(description),
            "link": link,
        })

    return results


def get_competitive_guide(keyword: str, my_char_count: int = 1500) -> dict:
    """상위 글 분석 기반 경쟁력 가이드를 생성한다.

    Args:
        keyword: 검색 키워드
        my_char_count: 내 글의 글자 수 (기본 1500)

    Returns:
        {"keyword", "avg_desc_length", "top_titles", "recommendation"}
    """
    posts = analyze_top_posts(keyword, count=5)

    if not posts:
        return {
            "keyword": keyword,
            "avg_desc_length": 0,
            "top_titles": [],
            "recommendation": "상위 글 데이터를 가져올 수 없습니다.",
        }

    avg_desc_length = sum(p["desc_length"] for p in posts) // len(posts)
    top_titles = [p["title"] for p in posts]

    # 내 글과 상위 글 평균 비교
    if my_char_count < avg_desc_length:
        diff = avg_desc_length - my_char_count
        recommendation = f"상위 글 평균보다 글이 짧습니다. {diff}자+ 추가 권장"
    else:
        recommendation = "현재 길이 적정"

    return {
        "keyword": keyword,
        "avg_desc_length": avg_desc_length,
        "top_titles": top_titles,
        "recommendation": recommendation,
    }


def build_competitor_prompt(guide: dict) -> str:
    """경쟁 분석 결과를 프롬프트용 텍스트로 변환한다 (200자 이내).

    Args:
        guide: get_competitive_guide() 반환값

    Returns:
        프롬프트에 삽입할 경쟁 분석 텍스트
    """
    avg_len = guide.get("avg_desc_length", 0)
    titles = guide.get("top_titles", [])

    # 상위 제목 패턴 요약 (3개까지)
    title_summary = ", ".join(titles[:3])
    if len(title_summary) > 80:
        title_summary = title_summary[:77] + "..."

    text = (
        "[경쟁 분석 - 상위 글보다 나은 글을 작성할 것]\n"
        f"상위 5개 평균 길이: {avg_len}자\n"
        f"상위 제목 패턴: {title_summary}"
    )

    # 200자 제한
    if len(text) > 200:
        text = text[:197] + "..."

    return text
