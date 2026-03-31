"""
음식점 상세 정보 수집 모듈
네이버 지역검색 API(주소, 전화번호, 카테고리) +
블로그 검색 API(영업시간, 주차, 라스트오더)를 조합하여 운영정보를 수집한다.
"""

import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

LOCAL_SEARCH_URL = "https://openapi.naver.com/v1/search/local.json"
BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"


def _get_search_headers() -> dict:
    """네이버 검색 API 인증 헤더를 반환한다."""
    return {
        "X-Naver-Client-Id": os.getenv("NAVER_CLIENT_ID", ""),
        "X-Naver-Client-Secret": os.getenv("NAVER_CLIENT_SECRET", ""),
    }


def _fetch_from_local_search(name: str) -> dict:
    """네이버 지역검색 API로 주소, 전화번호, 카테고리를 가져온다."""
    try:
        response = requests.get(
            LOCAL_SEARCH_URL,
            headers=_get_search_headers(),
            params={"query": name, "display": 1},
            timeout=10,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    except requests.RequestException:
        return {}

    if not items:
        return {}

    item = items[0]
    result = {}

    road_addr = item.get("roadAddress", "")
    if road_addr:
        result["road_address"] = road_addr

    addr = item.get("address", "")
    if addr:
        result["address"] = addr

    tel = item.get("telephone", "")
    if tel:
        result["telephone"] = tel

    category = item.get("category", "")
    if category:
        result["category"] = category

    title = re.sub(r"<[^>]+>", "", item.get("title", ""))
    if title:
        result["name"] = title

    return result


def fetch_place_detail(
    place_url: str = "",
    name: str = "",
    address: str = "",
) -> dict:
    """지역검색(주소/전화) + 블로그검색(영업시간/주차)을 조합하여 운영정보를 수집한다."""
    if not name:
        return {}

    # 1. 지역검색으로 주소/전화번호 (정형 데이터)
    local_info = _fetch_from_local_search(name)

    # 2. 블로그검색으로 영업시간/주차 (비정형 추출)
    blog_info = _fetch_from_blog_search(name)

    # 3. 합치기 (지역검색 우선, 블로그로 보충)
    merged = {**blog_info, **local_info}

    # 블로그에서만 나오는 항목 보충
    if not merged.get("business_hours") and blog_info.get("business_hours"):
        merged["business_hours"] = blog_info["business_hours"]
    if not merged.get("parking") and blog_info.get("parking"):
        merged["parking"] = blog_info["parking"]
    # 지역검색에 전화번호 없으면 블로그에서 보충
    if not merged.get("telephone") and blog_info.get("telephone"):
        merged["telephone"] = blog_info["telephone"]

    # 시설 정보 수집 (블로그에서 주차/화장실/접근성/편의시설)
    facility_info = _fetch_facility_info(name)
    merged.update(facility_info)

    # parking_details가 있는데 parking이 없으면 요약 생성
    if not merged.get("parking") and merged.get("parking_details"):
        merged["parking"] = merged["parking_details"][0]

    return merged


def _fetch_facility_info(name: str) -> dict:
    """블로그 검색에서 주차/화장실/접근성/편의시설 정보를 추출한다."""
    # 시설 정보 카테고리별 검색 키워드와 필터
    categories = {
        "parking_details": {
            "query": f"{name} 주차",
            "must_contain": ["주차", "주차장", "무료", "유료", "발렛"],
        },
        "restroom_info": {
            "query": f"{name} 화장실",
            "must_contain": ["화장실", "위생", "깨끗", "청결", "비밀번호", "공용"],
        },
        "access_info": {
            "query": f"{name} 위치 가는길",
            "must_contain": ["역", "도보", "걸어", "버스", "지하철", "출구", "골목", "건물"],
        },
        "facilities_info": {
            "query": f"{name} 단체 좌석",
            "must_contain": ["유아", "아기", "단체", "룸", "콘센트", "와이파이", "좌석"],
        },
    }

    # 노이즈 필터 (관련 없는 문장 제거)
    noise_words = [
        "다른곳", "다른 곳", "예전에", "저번에",
        "울었다", "장난", "뚜뚜", "옛땅", "경계지역",
        "테라스 좌석은 깊은", "앞바다", "목포 앞",
    ]

    result = {}
    for key, config in categories.items():
        try:
            response = requests.get(
                BLOG_SEARCH_URL,
                headers=_get_search_headers(),
                params={"query": config["query"], "display": 5, "sort": "sim"},
                timeout=10,
            )
            response.raise_for_status()
            items = response.json().get("items", [])
        except requests.RequestException:
            continue

        sentences = []
        seen = set()
        for item in items:
            desc = _strip_html(item.get("description", ""))
            for s in re.split(r"[.!?\n]", desc):
                s = s.strip()
                if len(s) < 8 or len(s) > 60 or s in seen:
                    continue
                if any(nw in s for nw in noise_words):
                    continue
                # 해당 카테고리 키워드가 있는 문장만
                kw_hits = sum(1 for kw in config["must_contain"] if kw in s)
                if kw_hits == 0:
                    continue
                # 한글 비율 체크 (역사/외국어 텍스트 필터)
                hangul = sum(1 for c in s if '가' <= c <= '힣')
                if hangul / max(len(s), 1) < 0.5:
                    continue
                seen.add(s)
                sentences.append(s)

        if sentences:
            result[key] = sentences[:2]

    return result


def _fetch_from_blog_search(name: str) -> dict:
    """네이버 블로그 검색 결과에서 가게 정보를 추출한다."""
    query = f"{name} 메뉴 영업시간 가격"

    try:
        response = requests.get(
            BLOG_SEARCH_URL,
            headers=_get_search_headers(),
            params={"query": query, "display": 5, "sort": "sim"},
            timeout=10,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    except requests.RequestException:
        return {}

    # 모든 블로그 결과의 텍스트를 합쳐서 정보 추출
    combined_text = ""
    for item in items:
        title = _strip_html(item.get("title", ""))
        desc = _strip_html(item.get("description", ""))
        combined_text += f"{title} {desc} "

    return _extract_info_from_text(combined_text)


def _strip_html(text: str) -> str:
    """HTML 태그를 제거한다."""
    return re.sub(r"<[^>]+>", "", text)


def _extract_info_from_text(text: str) -> dict:
    """텍스트에서 영업시간, 전화번호, 메뉴 등을 정규식으로 추출한다."""
    result = {}

    # 영업시간 추출
    hours_patterns = [
        r"영업시간[:\s]*(\d{1,2}:\d{2}\s*[-~]\s*\d{1,2}:\d{2})",
        r"(\d{1,2}:\d{2}\s*[-~]\s*\d{1,2}:\d{2})",
    ]
    for pattern in hours_patterns:
        match = re.search(pattern, text)
        if match:
            result["business_hours"] = match.group(1).strip()
            break

    # 전화번호 추출
    phone_patterns = [
        r"전화번호[:\s]*(0\d{1,3}[-\s]?\d{3,4}[-\s]?\d{4})",
        r"(0507[-\s]?\d{3,4}[-\s]?\d{4})",
        r"(02[-\s]?\d{3,4}[-\s]?\d{4})",
        r"(0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4})",
    ]
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            result["telephone"] = match.group(1).strip()
            break

    # 라스트오더 추출
    lo_pattern = r"라스트\s*오더[:\s]*(\d{1,2}:\d{2})"
    lo_match = re.search(lo_pattern, text)
    if lo_match:
        lo_time = lo_match.group(1)
        if result.get("business_hours"):
            result["business_hours"] += f" (라스트오더 {lo_time})"
        else:
            result["business_hours"] = f"라스트오더 {lo_time}"

    # 주차 추출 (주차 뒤에 가능/불가/무료/유료/발렛만 캡처)
    parking_match = re.search(r"주차[:\s]*(가능|불가능|불가|무료|유료|발렛)", text)
    if parking_match:
        result["parking"] = parking_match.group(1).strip()

    # 메뉴 추출 (가격 포함/미포함 모두)
    menus = []
    seen_normalized = set()  # 정규화된 키로 중복 방지

    def _normalize_course(name: str) -> str:
        """'코스 A' → 'A코스'로 통일한다."""
        name = name.strip().replace(" ", "")
        match = re.match(r"코스([A-Z])", name)
        if match:
            return f"{match.group(1)}코스"
        return name

    def _add_menu(name: str, price: str = ""):
        key = _normalize_course(name.strip())
        if key and len(key) >= 2 and key not in seen_normalized:
            seen_normalized.add(key)
            entry = f"{key} ({price})" if price else key
            menus.append(entry)

    # 가격 있는 메뉴
    price_patterns = [
        r"([A-Z]코스|코스\s*[A-Z])\s*[:\s]*(\d[\d,]+원)",
        r"([가-힣]+코스)\s*[:\s]*(\d[\d,]+원)",
        r"(오마카세)\s*[:\s]*(\d[\d,]+원)",
    ]
    for pattern in price_patterns:
        for name, price in re.findall(pattern, text):
            _add_menu(name, price)

    # 가격 없는 코스명 (A코스, B코스)
    course_matches = re.findall(r"([A-Z]코스|코스\s*[A-Z])", text)
    for name in course_matches:
        _add_menu(name)

    # 쉼표로 나열된 메뉴 추출 (육사시미, 우설, 꼬리구이, 특양, 막창)
    menu_enum = re.search(
        r"(육사시미|우설|특양|막창|꼬리구이|갈비|등심|채끝|안심)"
        r"(?:[,\s]+[가-힣]{2,6}){2,}",
        text,
    )
    if menu_enum:
        items = re.findall(r"[가-힣]{2,6}", menu_enum.group(0))
        # 노이즈 필터: 조사/어미가 붙은 단어 제거
        noise_suffixes = ("에서는", "이고", "이었", "으로", "처럼", "에는", "조림이", "이에요", "이랑")
        for item in items:
            if not item.endswith(noise_suffixes):
                _add_menu(item)

    if menus:
        result["menus"] = menus[:10]

    return result


def merge_place_info(search_result: dict, detail: dict) -> dict:
    """검색 결과와 상세 정보를 하나로 합친다."""
    telephone = (
        detail.get("telephone")
        or search_result.get("telephone")
        or ""
    )

    return {
        "name": search_result.get("title", ""),
        "category": search_result.get("category", ""),
        "telephone": telephone,
        "address": search_result.get("address", ""),
        "road_address": detail.get("road_address") or search_result.get("road_address", ""),
        "business_hours": detail.get("business_hours", ""),
        "menus": detail.get("menus", []),
        "parking": detail.get("parking", ""),
        "reservation": detail.get("reservation", ""),
        "link": search_result.get("link", ""),
        # 시설 정보 (블로그에서 자동 수집)
        "parking_details": detail.get("parking_details", []),
        "restroom_info": detail.get("restroom_info", []),
        "access_info": detail.get("access_info", []),
        "facilities_info": detail.get("facilities_info", []),
    }
