"""
메모 확장 모듈
짧은 메모를 내 블로그 말투로 3~4줄로 자동 확장한다.
학습된 스타일 프로필 기반으로 실제 내가 쓴 것처럼 변환.
"""

import os

from openai import OpenAI
from dotenv import load_dotenv

from modules.style_learner import get_style_profile, get_best_example_posts

load_dotenv()

EXPAND_MODEL = "gpt-4o-mini"  # 확장은 mini로 충분, 비용 절약


def _get_client() -> OpenAI:
    """OpenAI 클라이언트를 생성한다."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return OpenAI(api_key=api_key)


def expand_memo(short_memo: str, section: str = "일반") -> str:
    """짧은 메모를 내 말투로 3~4줄로 확장한다.

    Args:
        short_memo: 짧은 메모 (예: "깔끔하고 테이블 넓어 회식 좋음")
        section: 섹션 종류 ("외관", "내부", "분위기", "주차", "메뉴판", "총평", "일반")

    Returns:
        확장된 블로그 말투 텍스트 (3~4줄)
    """
    if not short_memo or not short_memo.strip():
        return ""

    # 학습된 프로필에서 말투 정보 가져오기
    profile = get_style_profile()
    style_hint = ""
    if profile:
        endings = [e[0] for e in profile.get("top_endings", [])[:4]]
        expressions = [e[0] for e in profile.get("top_expressions", [])[:4]]
        colloquials = [e[0] for e in profile.get("top_colloquials", [])[:5]]

        # 섹션별 실제 문장 샘플
        section_map = {"외관": "도입부", "내부": "도입부", "분위기": "도입부",
                       "메뉴판": "메뉴리뷰", "총평": "총평"}
        section_key = section_map.get(section, "도입부")
        section_samples = profile.get("section_samples", {}).get(section_key, [])[:3]
        sample_text = "\n".join([f'  "{s}"' for s in section_samples])

        style_hint = f"""내 말투 특징:
- 어미: {", ".join(endings)}
- 감탄사: {", ".join(expressions)}
- 구어체: {", ".join(colloquials)}
- 문장 평균 17자, 짧은 문장 위주

내가 비슷한 섹션에서 실제로 쓴 문장:
{sample_text}
"""

    # 실제 블로그 글에서 참고 문장 가져오기
    examples = get_best_example_posts(count=1)
    example_hint = ""
    if examples:
        # 해당 섹션에 맞는 부분만 추출 (짧게)
        example_hint = f"\n참고할 내 글 톤:\n{examples[0][:300]}...\n"

    section_guides = {
        "외관": "가게 외관/간판/위치 설명. 찾아가는 길, 주변 랜드마크 언급.",
        "내부": "내부 인테리어, 좌석 배치, 조명, 누구와 오면 좋을지.",
        "분위기": "전체적인 분위기, 소음, 청결도, 특별한 인테리어 포인트.",
        "주차": "주차 경험, 주차 가능 여부, 대안 교통수단.",
        "메뉴판": "메뉴 구성, 가격대, 뭘 고를지 고민한 과정.",
        "총평": "전체 만족도, 재방문 의사, 추천 포인트.",
        "일반": "자연스러운 블로그 문장으로 확장.",
    }
    guide = section_guides.get(section, section_guides["일반"])

    client = _get_client()
    response = client.chat.completions.create(
        model=EXPAND_MODEL,
        max_tokens=300,
        messages=[
            {
                "role": "system",
                "content": (
                    "네이버 블로그 맛집 리뷰어의 말투로 글을 쓴다. "
                    "~합니다/~됩니다 절대 사용 금지. "
                    "~했어요/~더라고요/~같아요 위주로 쓴다. "
                    "마크다운 문법 사용 금지. 짧은 문장 위주."
                ),
            },
            {
                "role": "user",
                "content": f"""아래 짧은 메모를 내 블로그 말투로 3~4줄로 자연스럽게 확장해줘.
줄바꿈 포함해서 블로그에 바로 붙여넣을 수 있게.
새로운 정보를 지어내지 말고, 메모 내용만 말투를 살려서 늘려줘.

{style_hint}
{example_hint}

섹션: {section} ({guide})

메모: "{short_memo}"

확장 (3~4줄, 줄바꿈 포함):""",
            },
        ],
    )

    return response.choices[0].message.content.strip()
