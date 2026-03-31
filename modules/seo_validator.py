"""
SEO 검증 모듈
본문의 키워드 밀도, 배치, 구조를 D.I.A+ 기준으로 검증한다.
"""

from modules.constants import (
    KEYWORD_DENSITY_TARGET,
    KEYWORD_MAX_REPEAT,
    PHOTO_MIN,
    PHOTO_MAX,
)


def validate_keyword_density(
    blog_text: str,
    top_keywords: list[dict],
) -> dict:
    """본문 내 키워드 밀도와 배치를 검증한다."""
    issues = []
    checks = {}

    # 해시태그/사진자리 제외한 순수 텍스트
    clean_lines = []
    for line in blog_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") or stripped in ("출처 입력", "사진 설명을 입력하세요."):
            continue
        clean_lines.append(stripped)
    clean_text = " ".join(clean_lines)
    total_chars = len(clean_text.replace(" ", ""))

    if total_chars == 0:
        return {"pass": False, "issues": ["본문이 비어있음"], "checks": {}}

    # 키워드 순서 추적용
    seo_checks_order = [kw.get("keyword", "") for kw in top_keywords[:3]]

    # 상위 3개 키워드 검증
    for kw_data in top_keywords[:3]:
        keyword = kw_data.get("keyword", "")
        kw_clean = keyword.replace(" ", "")
        if not kw_clean:
            continue

        # 출현 횟수
        count = clean_text.replace(" ", "").count(kw_clean)
        density = count / total_chars if total_chars > 0 else 0

        check = {
            "keyword": keyword,
            "count": count,
            "density_pct": round(density * 100, 2),
            "status": "pass",
        }

        # 밀도 검증: 출현 횟수 기반 (글자 밀도보다 실용적)
        # 1위 키워드 3~5회, 2~3위 키워드 2~3회가 적정
        rank = list(seo_checks_order).index(keyword) if keyword in seo_checks_order else 99
        min_count = 3 if rank == 0 else 2
        max_count = KEYWORD_MAX_REPEAT
        if count < min_count:
            check["status"] = "low"
            issues.append(f"'{keyword}' {count}회 → {min_count}회 이상 필요")
        elif density > 0.03:
            check["status"] = "high"
            issues.append(f"'{keyword}' 밀도 {check['density_pct']}% 과다 (스팸 위험)")

        # 최대 반복 검증
        if count > KEYWORD_MAX_REPEAT:
            check["status"] = "over_repeat"
            issues.append(f"'{keyword}' {count}회 반복 (최대 {KEYWORD_MAX_REPEAT}회)")

        checks[keyword] = check

    # 1위 키워드 서론 배치 확인
    if top_keywords:
        kw1 = top_keywords[0].get("keyword", "").replace(" ", "")
        first_3_lines = " ".join(clean_lines[:5]).replace(" ", "")
        if kw1 and kw1 not in first_3_lines:
            issues.append(f"1위 키워드 '{top_keywords[0]['keyword']}'가 서론(첫 5줄)에 없음")

    # 연속 2문장 동일 키워드 검출
    sentences = [s.strip() for s in clean_text.split(".") if s.strip()]
    for kw_data in top_keywords[:3]:
        kw = kw_data.get("keyword", "").replace(" ", "")
        if not kw:
            continue
        for i in range(len(sentences) - 1):
            s1 = sentences[i].replace(" ", "")
            s2 = sentences[i + 1].replace(" ", "")
            if kw in s1 and kw in s2:
                issues.append(f"'{kw_data['keyword']}' 연속 2문장 등장 (스팸 판정 위험)")
                break

    return {
        "pass": len(issues) == 0,
        "issues": issues,
        "checks": checks,
        "total_chars": total_chars,
    }


def validate_structure(blog_text: str) -> dict:
    """본문 구조를 검증한다. (사진 자리, 길이 등)"""
    issues = []

    # 사진 자리 수
    photo_count = blog_text.count("출처 입력")
    if photo_count < PHOTO_MIN:
        issues.append(f"사진 자리 {photo_count}개 (최소 {PHOTO_MIN}개)")
    elif photo_count > PHOTO_MAX:
        issues.append(f"사진 자리 {photo_count}개 (최대 {PHOTO_MAX}개)")

    # 본문 길이
    clean = blog_text.replace("출처 입력", "").replace("사진 설명을 입력하세요.", "")
    char_count = len(clean.replace(" ", "").replace("\n", ""))
    if char_count < 1500:
        issues.append(f"본문 {char_count}자 (1500자+ 권장)")
    elif char_count > 2500:
        issues.append(f"본문 {char_count}자 (2000자 이하 권장)")

    return {
        "pass": len(issues) == 0,
        "issues": issues,
        "photo_count": photo_count,
        "char_count": char_count,
    }


def run_seo_validation(
    blog_text: str,
    top_keywords: list[dict],
) -> dict:
    """키워드 밀도 + 구조 검증을 통합 실행한다."""
    density_result = validate_keyword_density(blog_text, top_keywords)
    structure_result = validate_structure(blog_text)

    all_issues = density_result["issues"] + structure_result["issues"]
    overall_pass = density_result["pass"] and structure_result["pass"]

    # 점수 산출 (100점 만점)
    score = 100 - (len(all_issues) * 10)
    score = max(0, min(100, score))

    if score >= 80:
        grade = "A"
    elif score >= 60:
        grade = "B"
    else:
        grade = "C"

    return {
        "pass": overall_pass,
        "score": score,
        "grade": grade,
        "issues": all_issues,
        "density": density_result,
        "structure": structure_result,
    }
