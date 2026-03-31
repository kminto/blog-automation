"""
키워드 점수 계산 모듈
검색량, 경쟁도, 트렌드를 종합하여 키워드 점수를 산출한다.
"""

from datetime import datetime, timedelta

from modules.constants import (
    COMPETITION_WEIGHTS,
    TREND_WEIGHTS,
    TOP_KEYWORDS_FOR_CONTENT,
    MIN_SEARCH_VOLUME,
    LONGTAIL_BONUS,
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


def _calc_longtail_bonus(keyword: str) -> float:
    """롱테일 키워드(3단어 이상)에 가산점을 부여한다."""
    # 공백 기준 단어 수 또는 키워드 길이로 판단
    word_count = len(keyword.split())
    char_count = len(keyword.replace(" ", ""))
    # 6자 이상이면서 조합 키워드면 롱테일로 판단
    if word_count >= 2 or char_count >= 6:
        return LONGTAIL_BONUS
    return 1.0


def score_keyword(
    keyword_data: dict,
    trend: str = "유지",
) -> dict:
    """단일 키워드의 최종 점수를 계산한다. (D.I.A+ 기반)"""
    search_volume = calculate_search_volume(keyword_data)
    comp_weight = get_competition_weight(keyword_data.get("compIdx", "중간"))
    trend_weight = TREND_WEIGHTS.get(trend, 1.0)
    keyword = keyword_data.get("relKeyword", "")
    longtail = _calc_longtail_bonus(keyword)

    # 점수 공식: (검색량 * 트렌드 * 롱테일 보너스) / 경쟁도
    final_score = (search_volume * trend_weight * longtail) / comp_weight

    return {
        "keyword": keyword,
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


def _get_used_keywords(days: int = 30) -> set[str]:
    """최근 N일 내 사용한 핵심 키워드를 로드한다."""
    try:
        from modules.blog_advisor import load_posting_log
        log = load_posting_log()
    except Exception:
        return set()

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    used = set()
    for record in log:
        if record.get("date", "") >= cutoff:
            for kw in record.get("keywords", []):
                used.add(kw)
    return used


def _check_keyword_overlap(keyword: str, used_keywords: set[str]) -> bool:
    """키워드가 이전에 사용된 키워드와 80% 이상 겹치는지 확인한다."""
    kw_clean = keyword.replace(" ", "")
    for used in used_keywords:
        used_clean = used.replace(" ", "")
        # 완전 일치
        if kw_clean == used_clean:
            return True
        # 80% 이상 겹침 (짧은 쪽 기준)
        shorter = min(len(kw_clean), len(used_clean))
        if shorter == 0:
            continue
        common = sum(1 for c in kw_clean if c in used_clean)
        if common / shorter >= 0.8:
            return True
    return False


def rank_keywords(
    scored_keywords: list[dict],
    top_n: int = TOP_KEYWORDS_FOR_CONTENT,
    regions: list[str] | None = None,
    menus: list[str] | None = None,
    check_duplicates: bool = True,
) -> list[dict]:
    """관련성 필터링 후 경쟁도 다양성을 확보하며 상위 N개를 반환한다."""
    # 이전 사용 키워드 로드 (중복 방지)
    used_keywords = _get_used_keywords() if check_duplicates else set()

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

    # 경쟁도별 분류 (최소 유의미 검색량 이상만)
    MIN_VOLUME = MIN_SEARCH_VOLUME
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
            # 중복 경고 표시
            if used_keywords and _check_keyword_overlap(kw["keyword"], used_keywords):
                kw["used_before"] = True
            result.append(kw)

    for kw in high:
        if kw["keyword"] not in seen:
            seen.add(kw["keyword"])
            if used_keywords and _check_keyword_overlap(kw["keyword"], used_keywords):
                kw["used_before"] = True
            result.append(kw)
        if len(result) >= top_n:
            break

    # 중복 키워드가 과반이면 경고 (자기잠식 위험)
    used_count = sum(1 for kw in result if kw.get("used_before"))
    if used_count > len(result) // 2 and result:
        result[0]["_dedup_warning"] = (
            f"주의: {used_count}/{len(result)}개 키워드가 최근 30일 내 사용됨. "
            "다른 지역/메뉴 조합을 시도하세요."
        )

    return result
