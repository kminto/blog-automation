"""
골드 예시 관리 모듈
사용자가 직접 수정한 최종본을 골드 예시로 저장/로드한다.
본문 생성 시 이 예시를 프롬프트에 넣으면 ChatGPT가 구조를 정확히 따라한다.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
GOLD_FILE = os.path.join(DATA_DIR, "gold_examples.json")


def save_gold_example(restaurant_name: str, final_text: str):
    """사용자가 수정 완료한 최종본을 골드 예시로 저장한다."""
    examples = load_gold_examples()

    examples.append({
        "restaurant": restaurant_name,
        "text": final_text,
        "length": len(final_text),
    })

    # 최대 5개 유지 (최신 우선)
    examples = examples[-5:]

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(GOLD_FILE, "w", encoding="utf-8") as f:
        json.dump(examples, f, ensure_ascii=False, indent=2)


def load_gold_examples() -> list[dict]:
    """저장된 골드 예시를 로드한다."""
    if not os.path.exists(GOLD_FILE):
        return []
    try:
        with open(GOLD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []


def get_best_gold_example() -> str:
    """가장 최근의 골드 예시를 반환한다. 없으면 빈 문자열."""
    examples = load_gold_examples()
    if not examples:
        return ""

    # 가장 최근 + 1500~2500자 범위 우선
    best = None
    for ex in reversed(examples):
        if 1200 <= ex.get("length", 0) <= 2500:
            best = ex
            break

    if not best and examples:
        best = examples[-1]

    text = best.get("text", "")
    # 너무 길면 자르기
    if len(text) > 2500:
        text = text[:2500] + "\n\n(이하 생략)"
    return text
