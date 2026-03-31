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

    # 지역 + 맛집 (필수 - 모든 지역에 대해 맛집 키워드 보장)
    for region in regions:
        combinations.add(f"{region}맛집")
        combinations.add(f"{region}맛집추천")
        combinations.add(f"{region}점심")

    # 지역 + 메뉴
    for region, menu in product(regions, menus):
        combinations.add(f"{region} {menu}")
        combinations.add(f"{region} {menu} 맛집")
        combinations.add(f"{region}{menu}")  # 붙여쓰기도 추가

    # 지역 + 상황
    for region, situation in product(regions, situations):
        combinations.add(f"{region} {situation}")

    # 지역 + 메뉴 + 상황
    for region, menu, situation in product(regions, menus, situations):
        keyword = f"{region} {menu} {situation}"
        combinations.add(keyword)

    # 지역별 균등 배분: 각 지역의 핵심 키워드가 잘리지 않도록
    # 지역+맛집 필수 키워드를 앞에 배치
    priority = []
    rest = []
    for kw in sorted(combinations):
        if any(kw.endswith("맛집") or kw.endswith("맛집추천") or kw.endswith("점심") for _ in [1]):
            priority.append(kw)
        else:
            rest.append(kw)

    result = priority + rest
    return result[:MAX_KEYWORD_COMBINATIONS * 2]  # 여유있게 100개


def filter_meaningful_keywords(keywords: list[str]) -> list[str]:
    """너무 짧거나 무의미한 키워드를 필터링한다."""
    return [kw for kw in keywords if len(kw) >= 4]
