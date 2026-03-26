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
    sections = {"titles": "", "body": "", "hashtags": ""}
    if "### 본문" in text:
        parts = text.split("### 본문")
        sections["titles"] = parts[0].replace("### 제목 후보", "").strip()
        body_part = parts[1]
        if "### 해시태그" in body_part:
            body_parts = body_part.split("### 해시태그")
            sections["body"] = body_parts[0].strip()
            sections["hashtags"] = body_parts[1].strip()
        else:
            sections["body"] = body_part.strip()
    else:
        sections["body"] = text
    return sections


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
