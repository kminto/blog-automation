"""
제목 생성 모듈
키워드 분석 결과를 기반으로 블로그 제목을 생성한다.
"""

import os

from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError
from dotenv import load_dotenv

from modules.constants import OPENAI_MODEL
from modules.prompt_builder import build_title_only_prompt

load_dotenv()


def generate_titles(
    restaurant_name: str,
    regions: list[str],
    menus: list[str],
    top_keywords: list[dict],
) -> str:
    """OpenAI API로 제목 후보를 생성한다."""
    prompt = build_title_only_prompt(
        restaurant_name=restaurant_name,
        regions=regions,
        menus=menus,
        top_keywords=top_keywords,
    )

    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except APIConnectionError:
        raise ConnectionError("OpenAI API 연결에 실패했습니다.")
    except RateLimitError:
        raise RuntimeError("API 호출 한도를 초과했습니다.")
    except APIStatusError as e:
        raise RuntimeError(f"OpenAI API 오류: {e.status_code}")
