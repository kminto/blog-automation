"""
시리즈/내부 링크 전략 모듈
같은 지역 포스팅을 시리즈로 묶고, 관련 글 내부 링크를 생성한다.
"""


def suggest_series(region: str, posting_log: list[dict]) -> dict:
    """같은 지역 글이 3개 이상이면 시리즈를 제안한다."""
    if not region or not posting_log:
        return {
            "has_series": False,
            "series_name": "",
            "current_count": 0,
            "restaurants": [],
        }

    # 같은 지역 글 필터링 (region 문자열 포함 여부)
    matched = [
        record for record in posting_log
        if region in record.get("region", "")
    ]

    count = len(matched)
    restaurants = [r.get("restaurant", "") for r in matched]

    if count >= 3:
        return {
            "has_series": True,
            "series_name": f"{region} 맛집 투어 {count}/{count + 2}",
            "current_count": count,
            "restaurants": restaurants,
        }

    return {
        "has_series": False,
        "series_name": "",
        "current_count": count,
        "restaurants": restaurants,
    }


def find_related_posts(
    region: str,
    category: str,
    posting_log: list[dict],
    exclude_restaurant: str = "",
) -> list[dict]:
    """같은 지역 또는 유사 키워드를 가진 이전 글 2~3개를 찾는다."""
    if not posting_log:
        return []

    scored = []
    for record in posting_log:
        # 현재 글 제외
        if exclude_restaurant and record.get("restaurant", "") == exclude_restaurant:
            continue

        score = 0
        # 같은 지역이면 가산
        if region and region in record.get("region", ""):
            score += 2

        # 키워드에 카테고리가 포함되면 가산
        keywords = record.get("keywords", [])
        if category and any(category in kw for kw in keywords):
            score += 1

        if score > 0:
            scored.append((score, record))

    # 점수 내림차순 → 최신 날짜 우선 정렬
    scored.sort(key=lambda x: (-x[0], x[1].get("date", "")), reverse=False)

    # 상위 3개만 반환 (새 딕셔너리 생성, 불변성 유지)
    results = []
    for _, record in scored[:3]:
        results.append({
            "restaurant": record.get("restaurant", ""),
            "title": record.get("title", ""),
            "date": record.get("date", ""),
            "keywords": list(record.get("keywords", [])),
        })

    return results


def build_internal_link_prompt(
    related_posts: list[dict],
    blog_id: str = "rinx_x",
) -> str:
    """관련 글 정보를 본문 생성용 프롬프트 텍스트로 변환한다."""
    if not related_posts:
        return ""

    lines = ["[관련 글 - 마무리에 자연스럽게 1~2개 언급할 것]"]
    for post in related_posts:
        restaurant = post.get("restaurant", "")
        title = post.get("title", "")
        date = post.get("date", "")
        # 날짜에서 날짜 부분만 추출 (시간 제거)
        date_short = date[:10] if len(date) >= 10 else date
        lines.append(f"- {title or restaurant} ({date_short})")

    return "\n".join(lines)
