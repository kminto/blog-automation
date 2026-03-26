"""
프롬프트 빌더 모듈
규칙 나열 대신 실제 블로그 예시 + 보이스 가이드 기반으로 자연스러운 글을 생성한다.
매 생성마다 톤/표현/구조를 랜덤으로 변주하여 AI 패턴 반복을 방지한다.
"""

import random

from modules.constants import TITLE_COUNT
from modules.voice_bank import (
    pick_voice_set,
    build_voice_guide,
    get_random_transitions,
)
from modules.example_posts import EXAMPLE_POSTS


def _build_ordered_menu_prompt(lines: list[str]) -> str:
    """주문 메뉴 입력을 프롬프트용 메뉴 리뷰 지시로 변환한다."""
    if not lines:
        return ""

    menus = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if " - " in line:
            name, desc = line.split(" - ", 1)
            menus.append({"name": name.strip(), "desc": desc.strip()})
        else:
            menus.append({"name": line, "desc": ""})

    if not menus:
        return ""

    drink_keywords = ["맥주", "소주", "사케", "와인", "음료", "하이볼", "콜라"]
    side_keywords = ["사이드", "디저트", "후식", "샐러드", "볶음밥"]

    main_menus = []
    side_menus = []
    for m in menus:
        if any(kw in m["name"] for kw in drink_keywords + side_keywords):
            side_menus.append(m)
        else:
            main_menus.append(m)

    result = "\n[내가 주문한 메뉴]\n"
    if main_menus:
        result += "메인:\n"
        for m in main_menus:
            desc = f" - {m['desc']}" if m["desc"] else ""
            result += f"  {m['name']}{desc}\n"
    if side_menus:
        result += "사이드/음료:\n"
        for m in side_menus:
            desc = f" - {m['desc']}" if m["desc"] else ""
            result += f"  {m['name']}{desc}\n"

    return result


def _pick_core_keywords(
    keywords: list[dict],
    regions: list[str],
    count: int = 3,
) -> list[dict]:
    """가게/지역 관련 키워드 중 검색량 높은 순으로 N개를 선별한다."""
    relevant = ["맛집", "고기", "술집", "오마카세", "구이", "회식", "데이트"]
    relevant.extend(regions)

    candidates = [
        kw for kw in keywords
        if any(term in kw["keyword"] for term in relevant)
    ]
    candidates.sort(key=lambda x: x["search_volume"], reverse=True)

    result = []
    seen = set()
    for kw in candidates:
        if kw["keyword"] not in seen:
            seen.add(kw["keyword"])
            result.append(kw)
        if len(result) >= count:
            break

    if len(result) < count:
        for kw in keywords:
            if kw["keyword"] not in seen:
                seen.add(kw["keyword"])
                result.append(kw)
            if len(result) >= count:
                break

    return result


def _build_keyword_table(keywords: list[dict]) -> str:
    """키워드 점수 데이터를 프롬프트용 테이블로 변환한다."""
    if not keywords:
        return "(키워드 데이터 없음)"

    lines = ["키워드 | 검색량 | 경쟁도 | 점수"]
    for kw in keywords[:10]:
        lines.append(
            f"{kw['keyword']} | {kw['search_volume']:,} | "
            f"{kw['competition']} | {kw['score']:,.0f}"
        )
    return "\n".join(lines)


def build_blog_prompt(
    restaurant_name: str,
    regions: list[str],
    menus: list[str],
    companion: str,
    mood: str,
    memo: str,
    top_keywords: list[dict],
) -> str:
    """블로그 본문 생성을 위한 프롬프트를 구성한다."""

    # 보이스 세트 랜덤 선택
    voice = pick_voice_set()
    voice_guide = build_voice_guide(voice)
    transitions = get_random_transitions()

    keyword_list = ", ".join([kw["keyword"] for kw in top_keywords])
    region_text = ", ".join(regions)
    core_3 = _pick_core_keywords(top_keywords, regions, 3)

    # 메모에서 주문 메뉴 / 후기 분리
    ordered_section = ""
    my_review_text = ""
    if "[내가 주문한 메뉴]" in memo:
        parts = memo.split("[내가 주문한 메뉴]")
        remaining = parts[1]
        if "[내 솔직 후기]" in remaining:
            menu_part, review_part = remaining.split("[내 솔직 후기]")
            ordered_lines = menu_part.strip().split("\n")
            my_review_text = review_part.strip()
        else:
            ordered_lines = remaining.strip().split("\n")
        memo = parts[0].strip()
        ordered_section = _build_ordered_menu_prompt(ordered_lines)
    elif "[내 솔직 후기]" in memo:
        parts = memo.split("[내 솔직 후기]")
        memo = parts[0].strip()
        my_review_text = parts[1].strip()

    menu_text = ", ".join(menus)

    # 예시 글 랜덤 1개 선택
    example = random.choice(EXAMPLE_POSTS)

    # 핵심 키워드 문자열
    kw1 = core_3[0]["keyword"] if core_3 else ""
    kw2 = core_3[1]["keyword"] if len(core_3) > 1 else ""
    kw3 = core_3[2]["keyword"] if len(core_3) > 2 else ""

    prompt = f"""당신은 네이버 블로그에 맛집 후기를 쓰는 블로거입니다.
아래 [실제 블로그 예시]와 똑같은 말투와 구조로 글을 써주세요.
규칙을 나열하지 않겠습니다. 예시 글의 톤, 문장 길이, 줄바꿈 패턴을 그대로 따라하세요.

[실제 블로그 예시 - 이 말투를 그대로 따라할 것]
{example}

---

[이번에 쓸 글 정보]
음식점: {restaurant_name}
지역: {region_text}
대표 메뉴: {menu_text}
동행: {companion or "미입력"}
분위기: {mood or "미입력"}
메모: {memo or "없음"}
{ordered_section}

[내 솔직 후기 - 이 내용이 글의 핵심]
{my_review_text or "후기 미입력 - 일반적인 긍정 리뷰로 작성"}

후기 활용 규칙:
- 위 후기 내용을 그대로 살려서 블로그 말투로 풀어쓸 것
- 내가 "맛없다", "아쉽다" 쓰면 그대로 반영 (좋게 바꾸지 말 것)
- 내가 안 먹은 메뉴를 지어내지 말 것
- 부족한 부분만 분위기/비주얼 묘사로 살짝 보충

[이번 글의 톤 설정]
{voice_guide}

[섹션 전환 표현 - 자연스럽게 사용]
내부로 넘어갈 때: "{transitions['to_interior']}"
메뉴 소개: "{transitions['to_menu']}"
음식 등장: "{transitions['to_food']}"
총평: "{transitions['to_closing']}"

[SEO 키워드]
본문에 자연스럽게 녹일 핵심 키워드:
1위: {kw1}  2위: {kw2}  3위: {kw3}

- 1위 키워드를 서론 + 중간 + 마무리에 3~4회 자연스럽게 삽입
- 나머지는 1~2회씩
- 억지로 넣지 말고 문맥에 맞게만

[작성 규칙 - 최소한만]

구조: 자유롭게. 예시 글처럼 자연스러운 흐름으로 작성.
단, 아래 요소는 반드시 포함:
1. 서론 (방문 계기 + 해시태그 3개)
2. [운영정보] 블록 (위치/운영시간/전화번호 등)
3. 내부 분위기 (사진 + 2~3줄)
4. 주문한 메뉴별 리뷰 (메뉴당 사진 2개 이상 + 솔직 감상)
5. 아쉬운 점 1개 (신뢰감)
6. 총평 + 재방문 의사
7. 해시태그 20개

금지:
- **, ##, --- 등 마크다운 문법
- "다양한", "풍부한", "맛의 하모니", "미각의 향연"
- ~합니다, ~됩니다 (격식체)
- "첫째, 둘째" 나열식
- ✏️ 표시나 수정 안내 (완성본을 쓸 것)
- 같은 표현("맛있었어요") 3회 이상 반복

필수:
- [사진: 말투로 설명] 형식 12곳 이상
- [움짤: 설명] 2곳 이상
- 1~2문장마다 줄바꿈 (긴 문단 절대 금지)
- 전체 2500자 이상
- 소제목은 이모지+텍스트 (📍, 🍽, 🍺, 🔚 등)

[출력 형식]

### 제목 후보
(SEO 키워드 앞배치, 25~40자, {TITLE_COUNT}개)

### 본문
(예시 글과 같은 말투의 완성된 블로그 본문)

### 해시태그
(20개, 공백 구분, 한 줄)
"""
    return prompt


def build_title_only_prompt(
    restaurant_name: str,
    regions: list[str],
    menus: list[str],
    top_keywords: list[dict],
) -> str:
    """제목만 생성하는 프롬프트를 구성한다."""
    keyword_table = _build_keyword_table(top_keywords)

    return f"""네이버 맛집 블로그 제목을 {TITLE_COUNT}개 추천해주세요.

음식점: {restaurant_name}
지역: {", ".join(regions)}
메뉴: {", ".join(menus)}

키워드 분석 데이터 (점수 높은 순):
{keyword_table}

제목 규칙:
- 공식: [검색량 높은 키워드] + [가게명] + [보조 키워드/감성 한마디]
- 앞쪽에 검색량 높은 키워드 배치
- 경쟁도 낮음/중간 키워드 우선
- 25~40자, 특수문자 없이
- 각각 다른 키워드 조합
"""
