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


def _build_optional_fields(
    companion: str, visit_reason: str, mood: str, memo: str,
) -> str:
    """입력된 항목만 프롬프트에 포함한다. 빈 항목은 완전히 제거."""
    lines = []
    if companion and companion.strip():
        lines.append(f"동행: {companion}")
    if visit_reason and visit_reason.strip():
        lines.append(f"방문 계기: {visit_reason}")
    if mood and mood.strip():
        lines.append(f"분위기: {mood}")
    if memo and memo.strip():
        lines.append(f"메모: {memo}")
    return "\n".join(lines)


def _build_place_info(place_detail: dict = None) -> str:
    """place_detail 딕셔너리를 프롬프트용 운영정보 텍스트로 변환한다."""
    if not place_detail:
        return ""

    lines = ["[운영정보 - 아래 내용을 [운영정보] 블록에 반드시 그대로 복사할 것. 절대 빈칸으로 두지 말 것]"]

    if place_detail.get("road_address"):
        lines.append(f"주소: {place_detail['road_address']}")
    elif place_detail.get("address"):
        lines.append(f"주소: {place_detail['address']}")

    if place_detail.get("business_hours"):
        lines.append(f"영업시간: {place_detail['business_hours']}")

    if place_detail.get("telephone"):
        lines.append(f"전화번호: {place_detail['telephone']}")

    if place_detail.get("parking"):
        lines.append(f"주차: {place_detail['parking']}")

    # 시설 정보 (블로그에서 수집 - 내 말투로 재작성 참고용, 복사 금지)
    facility_map = {
        "parking_details": "주차 참고",
        "restroom_info": "화장실 참고",
        "access_info": "접근성 참고",
        "facilities_info": "편의시설 참고",
    }
    for key, label in facility_map.items():
        details = place_detail.get(key, [])
        if details:
            lines.append(f"{label} (조합하여 내 말투로 새로 작성, 복사 금지):")
            for detail in details:
                lines.append(f"  - {detail}")

    # 정보가 주소밖에 없으면 빈 문자열 반환
    if len(lines) <= 1:
        return ""

    return "\n".join(lines)


def _build_detailed_review(detailed_review: dict = None) -> str:
    """세분화된 후기 딕셔너리를 프롬프트용 텍스트로 변환한다."""
    if not detailed_review:
        return ""

    sections = []

    # 반찬 리뷰
    side_dishes = detailed_review.get("side_dishes")
    if side_dishes:
        lines = ["[반찬 상세 리뷰 - 반드시 본문에 반영할 것]"]
        if side_dishes.get("items"):
            lines.append(f"반찬 종류: {side_dishes['items']}")
        if side_dishes.get("taste"):
            lines.append(f"맛 평가: {side_dishes['taste']}")
        if side_dishes.get("refill"):
            lines.append(f"리필 여부: {side_dishes['refill']}")
        if side_dishes.get("highlight"):
            lines.append(f"특히 맛있었던 반찬: {side_dishes['highlight']}")
        sections.append("\n".join(lines))

    # 메뉴별 상세 후기
    menu_reviews = detailed_review.get("menu_reviews")
    if menu_reviews:
        for mr in menu_reviews:
            lines = [f"[메뉴 상세: {mr.get('name', '?')} - 반드시 본문에 반영할 것]"]
            if mr.get("price"):
                lines.append(f"가격: {mr['price']}")
            if mr.get("taste"):
                lines.append(f"맛: {mr['taste']}")
            if mr.get("texture"):
                lines.append(f"식감: {mr['texture']}")
            if mr.get("spice"):
                lines.append(f"매운맛/간: {mr['spice']}")
            if mr.get("pairing"):
                lines.append(f"같이 먹으면 좋은 것: {mr['pairing']}")
            if mr.get("highlight"):
                lines.append(f"특이사항/포인트: {mr['highlight']}")
            if mr.get("one_liner"):
                lines.append(f"한줄평: {mr['one_liner']}")
            sections.append("\n".join(lines))

    # 서비스/친절도
    service = detailed_review.get("service")
    if service:
        lines = ["[서비스 평가 - 반드시 본문에 반영할 것]"]
        if service.get("staff"):
            lines.append(f"직원/사장님: {service['staff']}")
        if service.get("speed"):
            lines.append(f"음식 나오는 속도: {service['speed']}")
        if service.get("extras"):
            lines.append(f"서비스/추가 제공: {service['extras']}")
        sections.append("\n".join(lines))

    # 가격 평가
    price_eval = detailed_review.get("price_eval")
    if price_eval:
        sections.append(f"[가격 평가 - 본문 총평에 반영할 것]\n{price_eval}")

    # 재방문 의사
    revisit = detailed_review.get("revisit")
    if revisit:
        sections.append(f"[재방문 의사 - 본문 마무리에 반영할 것]\n{revisit}")

    # 추천 대상
    recommend_to = detailed_review.get("recommend_to")
    if recommend_to:
        sections.append(f"[추천 대상 - 본문 마무리에 반영할 것]\n{recommend_to}")

    # 아쉬운 점
    complaints = detailed_review.get("complaints")
    if complaints:
        sections.append(f"[아쉬운 점 - 솔직하게 본문에 1줄 반영할 것]\n{complaints}")

    # 다음에 먹어볼 메뉴
    next_menu = detailed_review.get("next_menu")
    if next_menu:
        sections.append(f"[다음에 먹어볼 메뉴 - 마무리에 반영할 것]\n{next_menu}")

    if not sections:
        return ""

    return "\n\n".join(sections)


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
    place_detail: dict = None,
    detailed_review: dict = None,
    visit_reason: str = "",
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

[이 블로거가 실제로 쓴 글 - 말투와 문체만 참고할 것]
주의: 아래 글의 음식점명, 지역, 메뉴는 절대 사용하지 말 것. 말투/어미/줄바꿈 패턴만 따라할 것.
{example}

---

[이번에 쓸 글 정보 - 반드시 이 정보만 사용할 것. 없는 항목은 절대 지어내지 말 것]
음식점: {restaurant_name}
지역: {region_text}
대표 메뉴: {menu_text}
{_build_optional_fields(companion, visit_reason, mood, memo)}
{ordered_section}
{_build_place_info(place_detail)}

[내 솔직 후기 - 이 내용이 글의 핵심]
{my_review_text or "후기 미입력 - 일반적인 긍정 리뷰로 작성"}

후기 활용 규칙:
- 위 후기 내용을 그대로 살려서 블로그 말투로 풀어쓸 것
- 내가 "맛없다", "아쉽다" 쓰면 그대로 반영 (좋게 바꾸지 말 것)
- 내가 안 먹은 메뉴를 지어내지 말 것
- 부족한 부분만 분위기/비주얼 묘사로 살짝 보충

{photo_context}

{_build_detailed_review(detailed_review)}

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

필수 구조 (서론 → 매장 → 본론 → 결론 순서):

[서론]
1. 인사 + 방문 계기 + 누구와 방문했는지 (3~4줄)
2. "출처 입력" + "사진 설명을 입력하세요." (외관 사진)

[매장 소개]
3. 위치/접근성 설명 (2~3줄)
4. "매장 정보" + [운영정보] 블록 (위에 제공된 운영정보를 그대로 복사. 비워두지 말 것)
5. "출처 입력" + 가게 외관/간판 사진
6. 주차 정보 (2~3줄, 위 주차 참고 내용 활용)
7. "가게 내부" + "출처 입력" + 내부 분위기/좌석/인테리어 묘사 (3~4줄)
8. 화장실/편의시설 (있으면 1줄)

[본론 - 음식 리뷰]
9. "기본 반찬" + "출처 입력" + 반찬 종류와 맛 (3~4줄)
10. "메인 메뉴 : 메뉴이름" + "출처 입력" 여러 개 + 맛/식감/비주얼 감상 (메뉴당 5줄+)
11. 사이드 메뉴 (있으면) + "출처 입력" + 감상 (2~3줄)

[결론]
12. 한줄평/총평 (2~3줄)
13. 재방문 의사 + 추천 대상 + 추천 이유 (2~3줄)
14. 마무리 인사 (1줄)

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
- 같은 어미 연속 2번 사용 금지 (~었어요 → ~더라고요 → ~거든요 식으로 매 문장 어미 변경)

어미 다양성 (매우 중요):
- ~었어요, ~더라고요만 반복하지 말 것
- 위 보이스 가이드의 어미 목록에서 최대한 다양하게 돌려쓸 것
- 감탄형(~대박이에요), 여운형(~생각나는 맛이에요), 솔직형(~나쁘지 않았어요), 질문형(~아닌가요?!) 등 섞어 쓸 것
- 특히 메뉴 리뷰 섹션에서 묘사 표현을 다채롭게 (식감/향/비주얼/간 등 감각 교차)

필수:
- 1~2문장마다 줄바꿈
- 전체 1500~2000자
- 소제목: 텍스트만 (이모지 소제목은 최소한으로)

[출력 형식]

### 제목 후보
(핵심 키워드 맨 앞 배치, 20~25자 이내, {TITLE_COUNT}개)

### 본문
(위 템플릿 구조대로, 네이버 에디터에 바로 붙여넣을 수 있는 형식)
(본문 안에 해시태그 넣지 말 것 - 해시태그는 별도 생성됨)
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
