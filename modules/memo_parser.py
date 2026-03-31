"""
퀵 모드 메모 파서 모듈
자유 메모 텍스트를 ChatGPT API로 구조화 데이터로 파싱한다.
"""

import json
import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def _get_client() -> OpenAI:
    """OpenAI 클라이언트를 생성한다."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return OpenAI(api_key=api_key)


def _build_parse_prompt(restaurant_name: str, memo_text: str) -> str:
    """메모 파싱용 프롬프트를 생성한다."""
    return f"""아래는 맛집 방문 후 사용자가 간단히 적은 메모입니다.
이 메모에서 블로그 글 작성에 필요한 정보를 추출하여 JSON으로 반환하세요.

음식점명: {restaurant_name}
메모:
{memo_text}

반드시 아래 JSON 스키마를 따르세요. 메모에 없는 정보는 빈 문자열("")로 두세요.
값을 지어내지 마세요. 메모에 있는 내용만 추출하세요.

{{
  "menus": ["메뉴명1", "메뉴명2"],
  "companion": "동행인 (예: 부모님, 친구)",
  "mood": "분위기/내부 묘사",
  "ordered_menus": "메뉴명 - 한줄평 (줄바꿈으로 구분)",
  "side_dishes": {{
    "items": "반찬 종류 나열",
    "taste": "반찬 맛 평가",
    "refill": "리필 여부",
    "highlight": "특히 맛있었던 반찬"
  }},
  "service": {{
    "staff": "사장님/직원 평가",
    "extras": "서비스/추가 제공 (리필, 직접 잘라줌 등)"
  }},
  "menu_reviews": [
    {{
      "name": "메뉴명",
      "price": "가격",
      "taste": "맛 묘사",
      "texture": "식감",
      "spice": "매운맛/간",
      "pairing": "같이 먹으면 좋은 것",
      "highlight": "특이사항/포인트",
      "one_liner": "한줄평"
    }}
  ],
  "price_eval": "가격 평가",
  "revisit": "재방문 의사",
  "recommend_to": "추천 대상",
  "complaints": "아쉬운 점",
  "next_menu": "다음에 먹어볼 메뉴"
}}"""


def _validate_parsed_result(data: dict) -> dict:
    """파싱 결과의 필수 필드를 검증하고 정리한다."""
    # menus가 문자열이면 리스트로 변환
    menus = data.get("menus", [])
    if isinstance(menus, str):
        menus = [m.strip() for m in menus.split(",") if m.strip()]
    data["menus"] = menus

    # detailed_review 조립
    detailed_review = {}

    sd = data.get("side_dishes", {})
    if isinstance(sd, dict) and any(sd.values()):
        detailed_review["side_dishes"] = {k: v for k, v in sd.items() if v}

    sv = data.get("service", {})
    if isinstance(sv, dict) and any(sv.values()):
        detailed_review["service"] = {k: v for k, v in sv.items() if v}

    mr = data.get("menu_reviews", [])
    if mr and isinstance(mr, list):
        valid_reviews = [r for r in mr if isinstance(r, dict) and r.get("name")]
        if valid_reviews:
            detailed_review["menu_reviews"] = valid_reviews

    for key in ["price_eval", "revisit", "recommend_to", "complaints", "next_menu"]:
        val = data.get(key, "")
        if val:
            detailed_review[key] = val

    data["detailed_review"] = detailed_review if detailed_review else None
    return data


def parse_quick_memo(restaurant_name: str, memo_text: str) -> dict:
    """자유 메모를 ChatGPT API로 구조화 데이터로 파싱한다."""
    if not memo_text or not memo_text.strip():
        return {
            "menus": [],
            "companion": "",
            "mood": "",
            "ordered_menus": "",
            "detailed_review": None,
        }

    client = _get_client()
    prompt = _build_parse_prompt(restaurant_name, memo_text)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=2048,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "맛집 메모에서 정보를 추출하는 파서입니다. JSON만 반환하세요.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    raw_text = response.choices[0].message.content
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "menus": [],
            "companion": "",
            "mood": "",
            "ordered_menus": memo_text,
            "detailed_review": None,
        }

    return _validate_parsed_result(parsed)
