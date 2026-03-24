"""
블로그 본문 생성 모듈
OpenAI ChatGPT API를 호출하여 블로그 글을 생성한다.
"""

import os

from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError
from dotenv import load_dotenv

from modules.constants import OPENAI_MODEL, OPENAI_MAX_TOKENS
from modules.prompt_builder import build_blog_prompt

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
                        "당신은 네이버 블로그 맛집 리뷰 전문 작가입니다. "
                        "사용자가 제공하는 음식점 정보와 방문 경험을 바탕으로 "
                        "자연스럽고 솔직한 맛집 리뷰 블로그 글을 작성합니다. "
                        "사용자의 개인 블로그에 게시할 창작 콘텐츠를 도와주세요."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content
    except APIConnectionError:
        raise ConnectionError("OpenAI API 연결에 실패했습니다. 네트워크를 확인해주세요.")
    except RateLimitError:
        raise RuntimeError("OpenAI API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
    except APIStatusError as e:
        raise RuntimeError(f"OpenAI API 오류가 발생했습니다: {e.status_code}")
