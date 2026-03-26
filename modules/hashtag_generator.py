"""
해시태그 생성 모듈
2026 SEO 기준: 5~9개로 정제. 핵심 2~3 + 세부 3~4 + 트렌드 1.
10개 이상은 SEO 효과 없음.
"""

from modules.constants import HASHTAG_MIN, HASHTAG_MAX


def generate_hashtags(
    restaurant_name: str,
    regions: list[str],
    menus: list[str],
    top_keywords: list[dict],
    mood: str = "",
) -> list[str]:
    """키워드 기반으로 해시태그 목록을 생성한다. (5~9개)"""

    # 1순위: 핵심 키워드 (검색량 높은 것 2~3개)
    core_tags = []
    for kw in top_keywords[:3]:
        keyword = kw.get("keyword", "").replace(" ", "")
        if keyword:
            core_tags.append(f"#{keyword}")

    # 2순위: 가게명 + 지역 세부 (3~4개)
    detail_tags = []
    clean_name = restaurant_name.replace(" ", "")
    detail_tags.append(f"#{clean_name}")
    for region in regions[:2]:
        detail_tags.append(f"#{region}맛집")
    if menus:
        detail_tags.append(f"#{regions[0] if regions else ''}{menus[0]}")

    # 3순위: 트렌드/상황 (1개)
    trend_tags = []
    if mood:
        first_mood = mood.split(",")[0].strip()
        if first_mood:
            trend_tags.append(f"#{first_mood}")
    if not trend_tags:
        trend_tags.append("#내돈내산")

    # 중복 제거 + 합치기
    seen = set()
    result = []
    for tag in core_tags + detail_tags + trend_tags:
        if tag not in seen and len(tag) > 1:
            seen.add(tag)
            result.append(tag)

    # 5~9개로 맞추기
    if len(result) > HASHTAG_MAX:
        result = result[:HASHTAG_MAX]

    return result
