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
from modules.style_learner import (
    get_style_profile,
    build_style_prompt_from_profile,
    get_best_example_posts,
)


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
    photo_context: str = "",
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

    # 학습된 내 블로그 예시가 있으면 우선 사용, 없으면 기본 예시
    my_examples = get_best_example_posts(count=1)
    if my_examples:
        example = my_examples[0]
        # 너무 길면 앞부분만 (3000자)
        if len(example) > 3000:
            example = example[:3000] + "\n\n(이하 생략)"
    else:
        example = random.choice(EXAMPLE_POSTS)

    # 학습된 스타일 프로필
    style_profile = get_style_profile()
    style_prompt = build_style_prompt_from_profile(style_profile) if style_profile else ""

    # 핵심 키워드 문자열
    kw1 = core_3[0]["keyword"] if core_3 else ""
    kw2 = core_3[1]["keyword"] if len(core_3) > 1 else ""
    kw3 = core_3[2]["keyword"] if len(core_3) > 2 else ""

    prompt = f"""당신은 네이버 블로그에 맛집 후기를 쓰는 블로거입니다.
아래는 이 블로거가 실제로 쓴 글과 말투 분석 결과입니다.
이 사람의 말투, 문장 길이, 줄바꿈 패턴, 감탄사 사용법을 완벽하게 따라하세요.
새로운 표현을 만들지 말고, 이 사람이 실제로 쓰는 표현만 사용하세요.

{style_prompt}

[이 블로거가 실제로 쓴 글 - 이 말투를 그대로 복제할 것]
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

{photo_context}

[이번 글의 톤 설정]
{voice_guide}

[섹션 전환 표현 - 자연스럽게 사용]
내부로 넘어갈 때: "{transitions['to_interior']}"
메뉴 소개: "{transitions['to_menu']}"
음식 등장: "{transitions['to_food']}"
총평: "{transitions['to_closing']}"

[SEO 키워드 전략 - 2026 네이버 D.I.A+ 기준]
본문에 녹일 핵심 키워드:
1위: {kw1}  2위: {kw2}  3위: {kw3}

키워드 삽입 규칙 (D.I.A+ 최적화):
- 전체 키워드 밀도 1.5~2% (과하면 스팸 판정)
- 1위 키워드: 서론 첫 문단 + 소제목 1개 + 마무리 = 3회
- 2~3위 키워드: 각 1~2회
- 동일 키워드 연속 2문장에 절대 넣지 말 것
- 동의어/유사어를 자연스럽게 섞어 쓸 것 (예: 맛집→맛집추천→맛집후기)

[작성 규칙 - 네이버 에디터 형식 + 2026 SEO]

아래 템플릿 구조를 반드시 따를 것. 예시 글의 형식을 그대로 복제.

필수 구조 (이 순서대로):
1. 인사 + 가게 소개 + 방문 계기 (3~4줄)
2. 해시태그 3~5개 (핵심 키워드)
3. "출처 입력" + "사진 설명을 입력하세요." (외관 사진 자리)
4. 위치 설명 2~3줄 + 기대감 한줄
5. "매장 정보" + [운영정보] 블록
6. "주차는?" 섹션 (2~3줄)
7. "가게 내부 분위기" + "출처 입력" + 내부 묘사 3~4줄
8. "셀프바 & 기본 반찬 리뷰" + "출처 입력" + 설명 2~3줄
9. "메인 메뉴 : 메뉴이름" + "출처 입력" 여러 개 + 맛 감상 (메뉴당 5줄+)
10. 사이드 메뉴 (있으면) + "출처 입력" + 감상 2~3줄
11. 한줄평/총평 3~4줄
12. 추천 대상 + 마무리 2~3줄
13. "🏷 해시태그" + 해시태그 7개

사진 자리 형식 (매우 중요):
- 사진이 들어갈 자리는 반드시 이렇게 표시:
  출처 입력
  사진 설명을 입력하세요.
- 이 두 줄이 한 세트. [사진: ] 형식 사용 금지.
- 메인 메뉴 섹션에는 "출처 입력" 3~4개
- 전체 "출처 입력" 8~12개

체류시간 극대화:
- 첫 3줄에 공감 문장
- 3문장 이상 이어지는 문단 금지
- 중간에 독자 질문 1~2개

금지:
- **, ##, --- 등 마크다운 문법
- [사진: ], [움짤: ] 형식 (네이버 에디터 형식 대신 사용)
- "다양한", "풍부한", "맛의 하모니", "미각의 향연"
- ~합니다, ~됩니다 (격식체)
- 같은 키워드 4회 이상 반복
- ✏️ 표시나 수정 안내

필수:
- 1~2문장마다 줄바꿈
- 전체 1500~2000자
- 소제목: 텍스트만 (이모지 소제목은 최소한으로)

[출력 형식]

### 제목 후보
(핵심 키워드 맨 앞 배치, 20~25자 이내, {TITLE_COUNT}개)

### 본문
(위 템플릿 구조대로, 네이버 에디터에 바로 붙여넣을 수 있는 형식)

### 해시태그
(7개, 공백 구분, 한 줄)
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
