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

    import re

    # 필터: 지역명이 아닌 것 제거
    noise = {"서울특별", "경기", "인천광역", "부산광역", "대구광역", "올림픽", "테헤란"}

    # 도로명주소 파싱
    if road_address:
        parts = road_address.split()
        for part in parts:
            # 시 단위 (성남시 → 성남, 서울특별시 제외)
            if part.endswith("시") and len(part) >= 3:
                city = part[:-1]
                if city not in noise:
                    _add(city)
            # 구 단위 (분당구 → 분당, 송파구 → 송파)
            if part.endswith("구") and len(part) >= 2:
                _add(part[:-1])
            # 도로명에서 지역명 추출 (판교역로 → 판교, 왕십리로 → 왕십리)
            road_match = re.match(r"([가-힣]{2,4})(역로|대로|로)", part)
            if road_match:
                name = road_match.group(1)
                # "역"으로 끝나면 제거 (판교역 → 판교)
                if name.endswith("역"):
                    name = name[:-1]
                if name not in noise and len(name) >= 2:
                    _add(name)

    # 지번주소에서 동/구 추출
    if jibun_address:
        for part in jibun_address.split():
            if part.endswith("구") and len(part) >= 2 and part[:-1] not in seen:
                _add(part[:-1])
            if part.endswith("동") and len(part) >= 2:
                _add(part)          # 삼평동
                _add(part[:-1])     # 삼평
                break
            if part.endswith("읍") or part.endswith("면"):
                _add(part)
                break

    # 지번주소가 없으면 도로명에서 동 이름 유추
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
