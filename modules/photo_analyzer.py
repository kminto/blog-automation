"""
사진 분석 모듈
OpenAI Vision API(gpt-4o)로 업로드된 사진을 자동 분류하고 묘사를 생성한다.
사진 순서: 외관 → 내부 → 메뉴판 → 반찬/세팅 → 메인음식 → 사이드/음료
"""

import base64
import json
import os

from openai import OpenAI
from dotenv import load_dotenv

PHOTO_ANALYSIS_MODEL = "gpt-4o-mini"  # 사진 분류는 mini로 충분, 비용 1/10

load_dotenv()

# 사진 카테고리 정의
PHOTO_CATEGORIES = [
    "외관",      # 가게 간판, 건물 외관
    "내부",      # 내부 인테리어, 좌석
    "메뉴판",    # 메뉴판, 가격표
    "세팅",      # 기본반찬, 셀프바, 테이블 세팅
    "메인음식",  # 메인 메뉴 음식
    "사이드",    # 사이드 메뉴, 음료, 주류
    "기타",      # 분류 불가
]


def _get_client() -> OpenAI:
    """OpenAI 클라이언트를 생성한다."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return OpenAI(api_key=api_key)


def _encode_image(image_bytes: bytes) -> str:
    """이미지를 base64로 인코딩한다."""
    return base64.b64encode(image_bytes).decode("utf-8")


def analyze_photos(photos: list[dict]) -> list[dict]:
    """여러 장의 사진을 한 번에 분석한다.

    Args:
        photos: [{"name": "파일명", "bytes": bytes데이터}, ...]

    Returns:
        [{"name": "파일명", "category": "메인음식", "description": "...", "details": {...}}, ...]
    """
    if not photos:
        return []

    client = _get_client()

    # 이미지를 메시지에 첨부
    content_parts = [
        {
            "type": "text",
            "text": f"""아래 {len(photos)}장의 사진은 맛집 방문 시 촬영한 사진들이야.
각 사진을 분석해서 JSON 배열로 답해줘. 다른 텍스트 없이 순수 JSON만 출력해.

각 사진마다:
1. category: 다음 중 하나 → "외관", "내부", "메뉴판", "세팅", "메인음식", "사이드", "기타"
2. food_name: 음식이면 메뉴 이름 (예: "돼지국밥", "양꼬치"), 음식 아니면 null
3. description: 블로그에 쓸 수 있는 묘사 1~2줄 (20대 여성 말투, "~에요", "~더라고요")
4. visual: 비주얼 특징 (색감, 플레이팅, 양, 크기 등)
5. atmosphere: 분위기/느낌 (아늑함, 깔끔함, 정겨움 등). 음식이면 null

JSON 형식:
[
  {{"index": 0, "category": "외관", "food_name": null, "description": "간판이 깔끔하게 보여요~", "visual": "깔끔한 간판, 밝은 조명", "atmosphere": "동네 맛집 느낌"}},
  {{"index": 1, "category": "메인음식", "food_name": "양꼬치", "description": "양꼬치 비주얼 미쳤어요,,", "visual": "10꼬치, 갈색 빛 숯불 자국", "atmosphere": null}}
]""",
        },
    ]

    for i, photo in enumerate(photos):
        b64 = _encode_image(photo["bytes"])
        content_parts.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64}",
                "detail": "low",  # 토큰 절약 (분류+간단 묘사에 충분)
            },
        })

    try:
        response = client.chat.completions.create(
            model=PHOTO_ANALYSIS_MODEL,
            max_tokens=2000,
            messages=[
                {
                    "role": "system",
                    "content": "맛집 사진을 분석하는 전문가. JSON만 출력한다.",
                },
                {"role": "user", "content": content_parts},
            ],
        )

        raw = response.choices[0].message.content.strip()
        # JSON 파싱 (```json ... ``` 감싸기 대응)
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        results = json.loads(raw)

        # 파일명 매핑
        for r in results:
            idx = r.get("index", 0)
            if idx < len(photos):
                r["name"] = photos[idx]["name"]

        return results

    except Exception as e:
        raise RuntimeError(f"사진 분석 오류: {e}")


def build_photo_context(analysis: list[dict]) -> str:
    """분석 결과를 프롬프트에 삽입할 텍스트로 변환한다."""
    if not analysis:
        return ""

    sections = {
        "외관": [], "내부": [], "메뉴판": [], "세팅": [],
        "메인음식": [], "사이드": [], "기타": [],
    }

    for item in analysis:
        cat = item.get("category", "기타")
        if cat not in sections:
            cat = "기타"
        sections[cat].append(item)

    lines = ["[사진 분석 결과 - 이 내용을 바탕으로 글을 작성할 것]"]

    # 카테고리별로 정리
    category_labels = {
        "외관": "🏪 가게 외관",
        "내부": "🪑 내부 분위기",
        "메뉴판": "📋 메뉴판",
        "세팅": "🥢 기본 세팅/반찬",
        "메인음식": "🍽 메인 음식",
        "사이드": "🍺 사이드/음료",
    }

    for cat, label in category_labels.items():
        items = sections.get(cat, [])
        if not items:
            continue
        lines.append(f"\n{label}:")
        for item in items:
            food = f" ({item['food_name']})" if item.get("food_name") else ""
            lines.append(f"  - {item.get('description', '')}{food}")
            if item.get("visual"):
                lines.append(f"    비주얼: {item['visual']}")
            if item.get("atmosphere"):
                lines.append(f"    분위기: {item['atmosphere']}")

    # 인식된 메뉴 자동 추출
    detected_menus = []
    for item in analysis:
        if item.get("food_name") and item.get("category") in ("메인음식", "사이드"):
            detected_menus.append(item["food_name"])

    if detected_menus:
        lines.append(f"\n사진에서 인식된 메뉴: {', '.join(detected_menus)}")

    return "\n".join(lines)


def extract_menus_from_analysis(analysis: list[dict]) -> list[str]:
    """분석 결과에서 메뉴 이름만 추출한다."""
    menus = []
    seen = set()
    for item in analysis:
        name = item.get("food_name")
        if name and name not in seen:
            seen.add(name)
            menus.append(name)
    return menus


def extract_descriptions_from_analysis(analysis: list[dict]) -> str:
    """분석 결과에서 자동 후기를 생성한다."""
    parts = []
    for item in analysis:
        if item.get("category") == "메인음식" and item.get("food_name"):
            desc = item.get("description", "")
            visual = item.get("visual", "")
            parts.append(f"{item['food_name']} - {desc} (비주얼: {visual})")
        elif item.get("category") == "사이드" and item.get("food_name"):
            parts.append(f"{item['food_name']} - {item.get('description', '')}")
    return "\n".join(parts)
