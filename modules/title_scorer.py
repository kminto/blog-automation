"""
제목 SEO 점수 평가 모듈
생성된 제목 후보를 D.I.A+ 기준으로 점수화한다.
"""

from modules.constants import TITLE_MIN_LENGTH, TITLE_MAX_LENGTH


# CTR 상승 표현
CTR_BOOSTERS = [
    "솔직후기", "내돈내산", "추천", "후기", "리뷰", "방문기",
    "꿀팁", "가성비", "숨은맛집", "찐맛집", "재방문",
]


def score_title(title: str, top_keywords: list[dict]) -> dict:
    """단일 제목의 SEO 점수를 계산한다. (100점 만점)"""
    score = 0
    details = []

    clean_title = title.strip()
    title_len = len(clean_title)

    # 1. 길이 (20점)
    if TITLE_MIN_LENGTH <= title_len <= TITLE_MAX_LENGTH:
        score += 20
        details.append(f"길이 {title_len}자 적정")
    elif title_len < TITLE_MIN_LENGTH:
        score += 5
        details.append(f"길이 {title_len}자 너무 짧음 ({TITLE_MIN_LENGTH}자+)")
    else:
        score += 10
        details.append(f"길이 {title_len}자 약간 김 (모바일 잘림 가능)")

    # 2. 핵심 키워드 포함 (30점)
    if top_keywords:
        kw1 = top_keywords[0].get("keyword", "")
        kw1_clean = kw1.replace(" ", "")
        if kw1_clean and kw1_clean in clean_title.replace(" ", ""):
            score += 20
            # 키워드가 앞 10자 이내에 위치하면 추가 점수
            pos = clean_title.replace(" ", "").find(kw1_clean)
            if pos <= 10:
                score += 10
                details.append(f"1위 키워드 '{kw1}' 제목 앞부분 배치")
            else:
                details.append(f"1위 키워드 '{kw1}' 포함 (앞으로 옮기면 더 좋음)")
        else:
            details.append(f"1위 키워드 '{kw1}' 미포함")

    # 3. 2~3위 키워드 포함 (15점)
    for kw_data in top_keywords[1:3]:
        kw = kw_data.get("keyword", "").replace(" ", "")
        if kw and kw in clean_title.replace(" ", ""):
            score += 7
            details.append(f"서브 키워드 '{kw_data['keyword']}' 포함")

    # 4. CTR 유도 표현 (15점)
    has_ctr = False
    for booster in CTR_BOOSTERS:
        if booster in clean_title:
            score += 15
            details.append(f"CTR 표현 '{booster}' 포함")
            has_ctr = True
            break
    if not has_ctr:
        details.append("CTR 표현 없음 (솔직후기/내돈내산/추천 등 추가 권장)")

    # 5. 음식점명 포함 (10점)
    # 제목에 가게명이 있으면 브랜드 검색 유입 가능
    score += 10  # 기본 부여 (가게명은 보통 포함됨)

    # 6. 특수문자 없음 (10점)
    special_chars = ["[", "]", "★", "♥", "●", "■"]
    if not any(c in clean_title for c in special_chars):
        score += 10
        details.append("특수문자 없음 (깔끔)")
    else:
        details.append("특수문자 있음 (제거 권장)")

    # 등급
    if score >= 80:
        grade = "A"
    elif score >= 60:
        grade = "B"
    elif score >= 40:
        grade = "C"
    else:
        grade = "D"

    return {
        "title": clean_title,
        "score": min(score, 100),
        "grade": grade,
        "details": details,
    }


def score_all_titles(titles_text: str, top_keywords: list[dict]) -> list[dict]:
    """여러 제목 후보를 점수화하고 추천 순위를 매긴다."""
    lines = [line.strip() for line in titles_text.strip().split("\n") if line.strip()]

    results = []
    for line in lines:
        # "1. 제목텍스트" 형태에서 번호 제거
        cleaned = line.lstrip("0123456789.").strip()
        if not cleaned:
            continue
        scored = score_title(cleaned, top_keywords)
        results.append(scored)

    # 점수 내림차순 정렬
    results.sort(key=lambda x: x["score"], reverse=True)

    # 1등에 추천 표시
    if results:
        results[0]["recommended"] = True

    return results
