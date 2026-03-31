"""
해시태그 생성 모듈
키워드 분석 결과 기반 경쟁력 높은 해시태그 20개 생성.
검색량 높은 키워드 + 롱테일 조합 + 지역/메뉴/상황 변형.
"""

from modules.constants import HASHTAG_MIN, HASHTAG_MAX


def generate_hashtags(
    restaurant_name: str,
    regions: list[str],
    menus: list[str],
    top_keywords: list[dict],
    mood: str = "",
) -> list[str]:
    """키워드 분석 결과 기반으로 경쟁력 있는 해시태그 20개를 생성한다."""

    seen = set()
    result = []

    def _add(tag: str):
        """중복 없이 해시태그 추가."""
        tag = tag.strip()
        if not tag.startswith("#"):
            tag = f"#{tag}"
        tag_clean = tag.replace(" ", "")
        if tag_clean not in seen and len(tag_clean) > 1:
            seen.add(tag_clean)
            result.append(tag_clean)

    # 1순위: 키워드 분석 상위 키워드 (검색량+점수 기반, 최대 10개)
    for kw in top_keywords[:10]:
        keyword = kw.get("keyword", "").replace(" ", "")
        if keyword:
            _add(keyword)

    # 2순위: 가게명
    clean_name = restaurant_name.replace(" ", "")
    _add(clean_name)

    # 3순위: 지역+맛집 변형
    for region in regions[:3]:
        _add(f"{region}맛집")
        _add(f"{region}맛집추천")

    # 4순위: 지역+메뉴 조합
    for region in regions[:2]:
        for menu in menus[:3]:
            menu_clean = menu.replace(" ", "")
            _add(f"{region}{menu_clean}")

    # 5순위: 메뉴 단독
    for menu in menus[:3]:
        menu_clean = menu.replace(" ", "")
        _add(menu_clean)
        _add(f"{menu_clean}맛집")

    # 6순위: 상황/분위기 태그
    if mood:
        mood_keywords = [m.strip() for m in mood.split(",") if m.strip()]
        for m in mood_keywords[:2]:
            m_clean = m.replace(" ", "")
            if len(m_clean) <= 10:
                _add(m_clean)

    # 7순위: 공통 트렌드 태그
    trend_tags = ["내돈내산", "맛집추천", "맛스타그램"]
    for tag in trend_tags:
        _add(tag)

    # 8순위: 지역+상황 조합 (부족하면)
    if len(result) < HASHTAG_MIN:
        situation_suffixes = ["데이트", "회식", "가족모임", "점심", "저녁"]
        for region in regions[:1]:
            for suffix in situation_suffixes:
                _add(f"{region}{suffix}")
                if len(result) >= HASHTAG_MAX:
                    break

    # 최대 개수로 자르기
    if len(result) > HASHTAG_MAX:
        result = result[:HASHTAG_MAX]

    return result
