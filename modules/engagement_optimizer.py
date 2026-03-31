"""
체류시간 최적화 모듈
D.I.A+ 체류시간 신호를 강화하는 요소를 검증한다.
"""

import re

from modules.constants import PHOTO_MIN, PHOTO_MAX


def validate_engagement(blog_text: str) -> dict:
    """본문의 체류시간 유도 요소를 검증하고 등급을 매긴다."""
    score = 0
    checks = []
    suggestions = []

    lines = [l.strip() for l in blog_text.split("\n") if l.strip()]
    clean_lines = [
        l for l in lines
        if l not in ("출처 입력", "사진 설명을 입력하세요.")
        and not l.startswith("#")
    ]
    clean_text = "\n".join(clean_lines)

    # 1. 첫 3줄에 공감/질문 문장 (20점)
    first_3 = " ".join(clean_lines[:3]) if len(clean_lines) >= 3 else ""
    engagement_starters = ["여러분", "혹시", "?", "추천", "소개", "다녀온", "안녕"]
    has_hook = any(word in first_3 for word in engagement_starters)
    if has_hook:
        score += 20
        checks.append("서론 훅 있음")
    else:
        suggestions.append("첫 3줄에 공감/질문 문장 추가 (예: '혹시 OO 찾고 계신가요?')")

    # 2. 질문형 문장 개수 (20점)
    questions = [l for l in clean_lines if "?" in l or l.endswith("가요") or l.endswith("세요")]
    q_count = len(questions)
    if q_count >= 2:
        score += 20
        checks.append(f"질문형 {q_count}개")
    elif q_count == 1:
        score += 10
        checks.append(f"질문형 {q_count}개 (2개+ 권장)")
        suggestions.append("질문 1개 더 추가 (예: '여기 가보신 분 있나요?')")
    else:
        suggestions.append("독자 참여 질문 2개 추가 (메뉴 리뷰 중간 + 마무리)")

    # 3. 사진 자리 수 (15점)
    photo_count = blog_text.count("출처 입력")
    if PHOTO_MIN <= photo_count <= PHOTO_MAX:
        score += 15
        checks.append(f"사진 {photo_count}개 적정")
    elif photo_count < PHOTO_MIN:
        suggestions.append(f"사진 자리 {photo_count}개 → {PHOTO_MIN}개 이상으로")
    else:
        suggestions.append(f"사진 자리 {photo_count}개 → {PHOTO_MAX}개 이하로")

    # 4. 문단 평균 길이 (15점) - 3줄 이하가 스크롤 유도
    paragraphs = re.split(r"\n\s*\n", clean_text)
    para_lengths = [len(p.split("\n")) for p in paragraphs if p.strip()]
    avg_para = sum(para_lengths) / len(para_lengths) if para_lengths else 0
    if avg_para <= 3:
        score += 15
        checks.append(f"문단 평균 {avg_para:.1f}줄 (짧은 호흡)")
    elif avg_para <= 5:
        score += 8
        checks.append(f"문단 평균 {avg_para:.1f}줄")
        suggestions.append("긴 문단을 2~3줄씩 나누면 스크롤 유도 효과")
    else:
        suggestions.append(f"문단 평균 {avg_para:.1f}줄 → 3줄 이하로 분리 필요")

    # 5. 소제목 개수 (15점) - 구조화로 스캔 유도
    subtitles = [l for l in lines if len(l) < 25 and not l.startswith("#")
                 and not l.startswith("출처") and any(
                     kw in l for kw in ["메뉴", "반찬", "분위기", "총평", "한줄평",
                                         "주차", "매장", "운영", "리뷰", "내부"]
                 )]
    if len(subtitles) >= 4:
        score += 15
        checks.append(f"소제목 {len(subtitles)}개")
    elif len(subtitles) >= 2:
        score += 8
        checks.append(f"소제목 {len(subtitles)}개 (4개+ 권장)")
    else:
        suggestions.append("소제목 추가 (매장정보, 메뉴리뷰, 총평 등)")

    # 6. 본문 길이 (15점)
    char_count = len(clean_text.replace(" ", "").replace("\n", ""))
    if 1500 <= char_count <= 2000:
        score += 15
        checks.append(f"본문 {char_count}자 적정")
    elif 1200 <= char_count < 1500:
        score += 8
        checks.append(f"본문 {char_count}자 (1500자+ 권장)")
    else:
        suggestions.append(f"본문 {char_count}자 → 1500~2000자로 조정")

    # 등급
    if score >= 80:
        grade = "A"
    elif score >= 60:
        grade = "B"
    else:
        grade = "C"

    return {
        "score": score,
        "grade": grade,
        "checks": checks,
        "suggestions": suggestions,
    }
