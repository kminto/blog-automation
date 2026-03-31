"""
UI 공통 헬퍼 함수
클립보드, 텍스트 파싱, 후기 조합 등 UI 전반에서 사용하는 유틸리티.
"""

import streamlit as st


def set_clipboard(key: str, text: str):
    """클립보드 복사용 세션 상태를 설정한다."""
    st.session_state[f"copied_{key}"] = text


def parse_blog_sections(text: str) -> dict:
    """생성된 블로그 텍스트에서 제목/본문/해시태그를 분리한다."""
    import re

    sections = {"titles": "", "body": "", "hashtags": ""}

    # 제목 섹션 분리 (### 제목 후보, ## 제목 후보, 제목 후보 등 유연하게)
    title_patterns = [r"#{1,3}\s*제목\s*후보", r"제목\s*후보"]
    body_patterns = [r"#{1,3}\s*본문"]
    hashtag_patterns = [r"#{1,3}\s*해시태그", r"🏷\s*해시태그"]

    # 본문 시작점 찾기
    body_start = 0
    for pattern in body_patterns:
        match = re.search(pattern, text)
        if match:
            # 제목 = 본문 시작 전까지
            title_part = text[:match.start()]
            for tp in title_patterns:
                title_part = re.sub(tp, "", title_part)
            sections["titles"] = _clean_markdown(title_part.strip())
            body_start = match.end()
            break

    remaining = text[body_start:]

    # 해시태그 시작점 찾기
    hashtag_start = len(remaining)
    for pattern in hashtag_patterns:
        match = re.search(pattern, remaining)
        if match:
            hashtag_start = match.start()
            sections["hashtags"] = remaining[match.end():].strip()
            # 해시태그 뒤에 또 다른 섹션이 있으면 잘라내기
            next_section = re.search(r"#{1,3}\s*(AI|품질|SEO)", sections["hashtags"])
            if next_section:
                sections["hashtags"] = sections["hashtags"][:next_section.start()].strip()
            break

    sections["body"] = _clean_markdown(remaining[:hashtag_start].strip())

    # 본문이 비어있으면 전체를 본문으로
    if not sections["body"]:
        sections["body"] = _clean_markdown(text)

    return sections


def _clean_markdown(text: str) -> str:
    """본문에서 마크다운 잔재를 제거하여 순수 텍스트로 만든다."""
    import re
    # ### 제목, ## 제목 제거 (줄 시작)
    text = re.sub(r"^#{1,3}\s+.+$", lambda m: m.group().lstrip("#").strip(), text, flags=re.MULTILINE)
    # **굵은글씨** 제거
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    # --- 구분선 제거
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)
    # 빈 줄 3개 이상 → 2개로
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def build_my_review(
    vibe: str, cook: str, wait: str, revisit: str,
    best: str, worst: str, episode: str, free: str,
) -> str:
    """분류형 입력을 하나의 후기 텍스트로 조합한다."""
    parts = [f"이 가게 핵심 포인트: {vibe}"]
    if cook != "해당없음":
        parts.append(f"조리 방식: {cook}")
    parts.append(f"웨이팅: {wait}")
    parts.append(f"재방문 의사: {revisit}")
    if best:
        parts.append(f"제일 맛있었던 것: {best}")
    if worst:
        parts.append(f"아쉬웠던 점: {worst}")
    if episode:
        parts.append(f"에피소드: {episode}")
    if free:
        parts.append(f"추가: {free}")
    return "\n".join(parts)


def build_auto_memo(info: dict) -> str:
    """수집된 정보로 자동 메모를 구성한다."""
    parts = []
    if info.get("business_hours"):
        parts.append(f"영업시간: {info['business_hours']}")
    if info.get("parking"):
        parts.append(f"주차: {info['parking']}")
    if info.get("reservation"):
        parts.append(f"예약: {info['reservation']}")
    if info.get("telephone"):
        parts.append(f"전화: {info['telephone']}")
    if info.get("facilities"):
        parts.append(f"편의시설: {', '.join(info['facilities'][:5])}")
    return "\n".join(parts)
