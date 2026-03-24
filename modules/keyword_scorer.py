"""
키워드 점수 계산 모듈
검색량, 경쟁도, 트렌드를 종합하여 키워드 점수를 산출한다.
"""

from modules.constants import (
    COMPETITION_WEIGHTS,
    TREND_WEIGHTS,
    TOP_KEYWORDS_FOR_CONTENT,
)


def calculate_search_volume(keyword_data: dict) -> int:
    """PC + 모바일 검색량 합산을 계산한다."""
    pc = keyword_data.get("monthlyPcQcCnt", 0)
    mobile = keyword_data.get("monthlyMobileQcCnt", 0)

    # "< 10" 같은 문자열 처리
    if isinstance(pc, str):
        pc = 5 if "<" in pc else int(pc)
    if isinstance(mobile, str):
        mobile = 5 if "<" in mobile else int(mobile)

    return pc + mobile


def get_competition_weight(comp_idx: str) -> float:
    """경쟁도 문자열을 숫자 가중치로 변환한다."""
    return COMPETITION_WEIGHTS.get(comp_idx, 1.0)


def score_keyword(
    keyword_data: dict,
    trend: str = "유지",
) -> dict:
    """단일 키워드의 최종 점수를 계산한다."""
    search_volume = calculate_search_volume(keyword_data)
    comp_weight = get_competition_weight(keyword_data.get("compIdx", "중간"))
    trend_weight = TREND_WEIGHTS.get(trend, 1.0)

    # 점수 공식: (검색량 * 트렌드 가중치) / 경쟁도 가중치
    final_score = (search_volume * trend_weight) / comp_weight

    return {
        "keyword": keyword_data.get("relKeyword", ""),
        "search_volume": search_volume,
        "competition": keyword_data.get("compIdx", "중간"),
        "trend": trend,
        "score": round(final_score, 1),
    }


def filter_relevant_keywords(
    scored_keywords: list[dict],
    regions: list[str],
    menus: list[str],
) -> list[dict]:
    """입력한 지역/메뉴와 관련된 키워드만 필터링하고 중복을 제거한다."""
    # 관련성 판단용 키워드 집합
    relevant_terms = set()
    for region in regions:
        relevant_terms.add(region)
    for menu in menus:
        relevant_terms.add(menu)

    filtered = []
    seen = set()

    for kw_data in scored_keywords:
        keyword = kw_data["keyword"]

        # 중복 제거
        if keyword in seen:
            continue
        seen.add(keyword)

        # 지역 또는 메뉴 키워드가 포함된 것만 통과
        has_relevance = any(term in keyword for term in relevant_terms)
        if has_relevance:
            filtered.append(kw_data)

    return filtered


def rank_keywords(
    scored_keywords: list[dict],
    top_n: int = TOP_KEYWORDS_FOR_CONTENT,
    regions: list[str] | None = None,
    menus: list[str] | None = None,
) -> list[dict]:
    """관련성 필터링 후 경쟁도 다양성을 확보하며 상위 N개를 반환한다."""
    # 지역/메뉴 정보가 있으면 관련 키워드만 필터링
    if regions or menus:
        scored_keywords = filter_relevant_keywords(
            scored_keywords,
            regions=regions or [],
            menus=menus or [],
        )

    sorted_keywords = sorted(
        scored_keywords,
        key=lambda x: x["score"],
        reverse=True,
    )

    # 경쟁도별 분류 (최소 검색량 100 이상만)
    MIN_VOLUME = 100
    low_mid = [
        kw for kw in sorted_keywords
        if kw["competition"] in ("낮음", "중간") and kw["search_volume"] >= MIN_VOLUME
    ]
    high = [
        kw for kw in sorted_keywords
        if kw["competition"] == "높음" and kw["search_volume"] >= MIN_VOLUME
    ]

    # 낮음/중간 최대 4개 + 높음으로 나머지 채우기 (검색량 볼륨 확보)
    max_low_mid = min(4, len(low_mid))
    result = []
    seen = set()

    for kw in low_mid[:max_low_mid]:
        if kw["keyword"] not in seen:
            seen.add(kw["keyword"])
            result.append(kw)

    for kw in high:
        if kw["keyword"] not in seen:
            seen.add(kw["keyword"])
            result.append(kw)
        if len(result) >= top_n:
            break

    return result
