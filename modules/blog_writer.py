"""
블로그 본문 생성 모듈
OpenAI ChatGPT API를 호출하여 블로그 글을 생성한다.
"""

import os

from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError
from dotenv import load_dotenv

from modules.constants import OPENAI_MODEL, OPENAI_MAX_TOKENS
from modules.prompt_builder import build_blog_prompt
from modules.post_processor import process_blog_text

load_dotenv()


def _get_openai_client() -> OpenAI:
    """OpenAI API 클라이언트를 생성한다."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return OpenAI(api_key=api_key)


def generate_blog_post(
    restaurant_name: str,
    regions: list[str],
    menus: list[str],
    companion: str,
    mood: str,
    memo: str,
    top_keywords: list[dict],
) -> str:
    """블로그 본문을 생성한다."""
    prompt = build_blog_prompt(
        restaurant_name=restaurant_name,
        regions=regions,
        menus=menus,
        companion=companion,
        mood=mood,
        memo=memo,
        top_keywords=top_keywords,
    )

    try:
        client = _get_openai_client()
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=OPENAI_MAX_TOKENS,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 네이버 블로그에 맛집 후기를 올리는 20대 후반 여성 블로거입니다. "
                        "친구한테 카톡으로 맛집 추천하듯 솔직하고 편하게 씁니다. "
                        "AI가 쓴 것처럼 보이면 안 됩니다. 실제 사람이 쓴 블로그처럼 써주세요. "
                        "~합니다 대신 ~했어요/~더라고요를 쓰고, 줄바꿈을 자주 합니다."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        raw_text = response.choices[0].message.content
        # AI 냄새 후처리 (격식체→구어체, 반복 표현 교체, 마크다운 잔재 정리)
        return process_blog_text(raw_text)
    except APIConnectionError:
        raise ConnectionError("OpenAI API 연결에 실패했습니다. 네트워크를 확인해주세요.")
    except RateLimitError:
        raise RuntimeError("OpenAI API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
    except APIStatusError as e:
        raise RuntimeError(f"OpenAI API 오류가 발생했습니다: {e.status_code}")
