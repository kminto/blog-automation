"""
네이버 지역검색 API 모듈
음식점 이름으로 검색하여 기본 정보(주소, 카테고리, 전화번호 등)를 가져온다.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

LOCAL_SEARCH_URL = "https://openapi.naver.com/v1/search/local.json"


def _get_search_headers() -> dict:
    """네이버 검색 API 인증 헤더를 반환한다."""
    return {
        "X-Naver-Client-Id": os.getenv("NAVER_CLIENT_ID", ""),
        "X-Naver-Client-Secret": os.getenv("NAVER_CLIENT_SECRET", ""),
    }


def search_restaurant(query: str, display: int = 5) -> list[dict]:
    """음식점 이름으로 네이버 지역검색을 수행한다."""
    if not query or not query.strip():
        raise ValueError("검색어를 입력해주세요.")

    params = {
        "query": query.strip(),
        "display": display,
        "sort": "random",
    }

    try:
        response = requests.get(
            LOCAL_SEARCH_URL,
            headers=_get_search_headers(),
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        return [_clean_item(item) for item in items]
    except requests.RequestException as e:
        raise RuntimeError(f"네이버 지역검색 API 오류: {e}")


def _clean_item(item: dict) -> dict:
    """검색 결과에서 HTML 태그를 제거하고 정리한다."""
    title = item.get("title", "")
    # <b> 태그 제거
    title = title.replace("<b>", "").replace("</b>", "")

    return {
        "title": title,
        "category": item.get("category", ""),
        "telephone": item.get("telephone", ""),
        "address": item.get("address", ""),
        "road_address": item.get("roadAddress", ""),
        "link": item.get("link", ""),
        "mapx": item.get("mapx", ""),
        "mapy": item.get("mapy", ""),
    }


def extract_region_from_address(
    road_address: str,
    jibun_address: str = "",
) -> list[str]:
    """도로명주소 + 지번주소에서 지역명을 추출한다."""
    regions = []
    seen = set()

    def _add(name: str):
        if name and name not in seen:
            seen.add(name)
            regions.append(name)

    # 도로명주소 파싱
    if road_address:
        parts = road_address.split()
        if len(parts) >= 2:
            # 구 단위 (송파구 → 송파)
            gu = parts[1].replace("시", "").replace("군", "").replace("구", "")
            _add(gu)

    # 지번주소에서 동 추출 (예: 서울특별시 송파구 방이동 149-9)
    if jibun_address:
        for part in jibun_address.split():
            if part.endswith("동") and len(part) >= 2:
                _add(part)          # 방이동
                _add(part[:-1])     # 방이
                break
            if part.endswith("읍") or part.endswith("면"):
                _add(part)
                break

    # 지번주소가 없으면 도로명에서 동 이름 유추 시도
    if not jibun_address and road_address:
        for part in road_address.split():
            if part.endswith("동") and len(part) >= 3:
                _add(part)
                break

    return regions


def extract_menus_from_category(category: str) -> list[str]:
    """카테고리에서 메뉴 힌트를 추출한다."""
    if not category:
        return []

    # 카테고리 예시: "한식>국밥" or "음식점>한식>돼지국밥"
    parts = category.split(">")
    menus = []

    for part in parts:
        part = part.strip()
        # 너무 일반적인 카테고리 제외
        generic = {"음식점", "한식", "중식", "일식", "양식", "분식", "카페", "술집"}
        if part and part not in generic:
            menus.append(part)

    return menus
