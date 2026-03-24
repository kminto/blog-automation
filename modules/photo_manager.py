"""
사진 관리 모듈
촬영 가이드 생성 + 업로드 사진을 본문 슬롯에 자동 매칭한다.
"""


# === 촬영 가이드 (이 순서대로 찍으면 됨) ===
PHOTO_SHOT_GUIDE = [
    {"slot": 1, "label": "외관", "tip": "가게 간판이 보이게 정면에서 한 장"},
    {"slot": 2, "label": "간판/입구", "tip": "간판 클로즈업 또는 입구"},
    {"slot": 3, "label": "내부 전경", "tip": "자리에 앉아서 매장 전체 한 장"},
    {"slot": 4, "label": "테이블 세팅", "tip": "내 테이블 세팅 모습"},
    {"slot": 5, "label": "메뉴판", "tip": "메뉴판 전체가 보이게"},
    {"slot": 6, "label": "기본반찬/셀프바", "tip": "기본 세팅 or 셀프바"},
    {"slot": 7, "label": "메인1 - 전체샷", "tip": "첫 번째 메인 메뉴 전체 모습"},
    {"slot": 8, "label": "메인1 - 클로즈업", "tip": "첫 번째 메뉴 맛있어 보이는 각도"},
    {"slot": 9, "label": "메인1 - 조리/먹는중", "tip": "굽는 중, 먹는 중 등 액션샷 (움짤용)"},
    {"slot": 10, "label": "메인2 - 전체샷", "tip": "두 번째 메인 메뉴"},
    {"slot": 11, "label": "메인2 - 클로즈업", "tip": "두 번째 메뉴 클로즈업"},
    {"slot": 12, "label": "사이드 메뉴", "tip": "음료, 사이드, 디저트 등"},
    {"slot": 13, "label": "먹방샷", "tip": "먹고 있는 모습 or 완식 샷 (선택)"},
]


def get_shot_guide() -> list[dict]:
    """촬영 가이드를 반환한다."""
    return PHOTO_SHOT_GUIDE


def replace_photo_slots(blog_text: str, photo_map: dict) -> str:
    """본문의 [사진: ...] 슬롯을 실제 이미지 태그로 교체한다.

    photo_map: {1: uploaded_file, 2: uploaded_file, ...}
    """
    import re

    # 본문에서 [사진: ...] 과 [움짤: ...] 을 순서대로 찾기
    pattern = r"\[(사진|움짤):\s*([^\]]*)\]"
    matches = list(re.finditer(pattern, blog_text))

    if not matches:
        return blog_text

    # 슬롯 번호순으로 매칭
    result = blog_text
    for idx, match in enumerate(reversed(matches)):
        slot_num = len(matches) - idx  # 역순이므로
        if slot_num in photo_map:
            # 이미지 HTML로 교체
            img_tag = (
                f'<div style="text-align:center;margin:12px 0;">'
                f'<img src="data:image/jpeg;base64,{{photo_b64_{slot_num}}}" '
                f'style="max-width:100%;border-radius:8px;" />'
                f'<p style="color:#888;font-size:13px;margin-top:4px;">'
                f'{match.group(2)}</p></div>'
            )
            result = result[:match.start()] + img_tag + result[match.end():]

    return result


def build_photo_checklist_text() -> str:
    """촬영 체크리스트를 텍스트로 반환한다. (방문 전 확인용)"""
    lines = ["📸 촬영 가이드 (이 순서대로 찍으세요!)", ""]
    for shot in PHOTO_SHOT_GUIDE:
        lines.append(f"  {shot['slot']:2d}번 | {shot['label']:15s} | {shot['tip']}")
    lines.append("")
    lines.append("💡 팁: 세로 사진이 블로그에서 더 예뻐요!")
    lines.append("💡 팁: 음식은 45도 각도에서 찍으면 맛있어 보여요!")
    return "\n".join(lines)
