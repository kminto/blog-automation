"""
해시태그 생성 모듈
키워드와 음식점 정보를 기반으로 해시태그를 생성한다.
"""

from modules.constants import HASHTAG_MIN, HASHTAG_MAX


def generate_hashtags(
    restaurant_name: str,
    regions: list[str],
    menus: list[str],
    top_keywords: list[dict],
    mood: str = "",
) -> list[str]:
    """키워드 기반으로 해시태그 목록을 생성한다."""
    hashtags = set()

    # 음식점 이름
    hashtags.add(f"#{restaurant_name.replace(' ', '')}")

    # 지역 기반
    for region in regions:
        hashtags.add(f"#{region}맛집")
        hashtags.add(f"#{region}")
        for menu in menus:
            hashtags.add(f"#{region}{menu}")

    # 메뉴 기반
    for menu in menus:
        hashtags.add(f"#{menu}")
        hashtags.add(f"#{menu}맛집")
        hashtags.add(f"#{menu}추천")

    # 분위기 기반
    if mood:
        for m in mood.split(","):
            m = m.strip()
            if m:
                hashtags.add(f"#{m}")

    # 상위 키워드 기반
    for kw_data in top_keywords:
        keyword = kw_data.get("keyword", "").replace(" ", "")
        if keyword:
            hashtags.add(f"#{keyword}")

    # 공통 해시태그
    common_tags = ["#맛집", "#맛집추천", "#맛스타그램", "#먹스타그램",
                   "#맛집탐방", "#오늘뭐먹지", "#맛집기록"]
    for tag in common_tags:
        hashtags.add(tag)

    result = sorted(hashtags)

    # 최소/최대 개수 조정
    if len(result) > HASHTAG_MAX:
        result = result[:HASHTAG_MAX]

    return result
