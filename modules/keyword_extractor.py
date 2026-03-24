"""
키워드 조합 생성 모듈
지역, 메뉴, 상황 키워드를 조합하여 검색 후보 키워드를 생성한다.
"""

from itertools import product
from modules.constants import SITUATION_KEYWORDS, MAX_KEYWORD_COMBINATIONS


def generate_keyword_combinations(
    regions: list[str],
    menus: list[str],
    situations: list[str] | None = None,
) -> list[str]:
    """지역 + 메뉴 + 상황 키워드 조합을 생성한다."""
    if situations is None:
        situations = SITUATION_KEYWORDS

    combinations = set()

    # 지역 + 메뉴
    for region, menu in product(regions, menus):
        combinations.add(f"{region} {menu}")
        combinations.add(f"{region} {menu} 맛집")

    # 지역 + 상황
    for region, situation in product(regions, situations):
        combinations.add(f"{region} {situation}")

    # 지역 + 메뉴 + 상황
    for region, menu, situation in product(regions, menus, situations):
        keyword = f"{region} {menu} {situation}"
        combinations.add(keyword)

    # 중복 제거 후 정렬
    result = sorted(combinations)

    # 상위 후보만 반환
    return result[:MAX_KEYWORD_COMBINATIONS]


def filter_meaningful_keywords(keywords: list[str]) -> list[str]:
    """너무 짧거나 무의미한 키워드를 필터링한다."""
    return [kw for kw in keywords if len(kw) >= 4]
