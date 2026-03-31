"""
블로그 생성 결과 표시 모듈
제목/본문/해시태그를 섹션별로 렌더링한다.
"""

import streamlit as st

from modules.gold_examples import save_gold_example
from modules.post_processor import get_ai_score
from modules.seo_validator import run_seo_validation
from modules.engagement_optimizer import validate_engagement
from ui.helpers import parse_blog_sections


def _render_quality_report(body_text: str):
    """품질 리포트를 본문 위에 항상 표시한다."""
    seo = st.session_state.get("seo_validation")
    eng = st.session_state.get("engagement")
    ai = st.session_state.get("ai_check")
    pub = st.session_state.get("publish_time")

    if not seo and not eng:
        return

    # 종합 점수 계산
    scores = []
    if ai:
        scores.append(("AI 냄새", ai.get("score", 0), ai.get("grade", "")))
    if seo:
        scores.append(("SEO", seo.get("score", 0), seo.get("grade", "")))
    if eng:
        scores.append(("체류시간", eng.get("score", 0), eng.get("grade", "")))

    # 종합 등급 판정
    grades = [s[2] for s in scores]
    if all(g in ("A", "좋음") for g in grades):
        overall = "🟢 우수"
    elif any(g in ("C", "개선필요") for g in grades):
        overall = "🔴 개선필요"
    else:
        overall = "🟡 양호"

    st.subheader(f"📊 품질 리포트 — {overall}")

    # 점수 카드
    cols = st.columns(len(scores) + (1 if pub else 0))
    emoji_map = {"A": "🟢", "B": "🟡", "C": "🔴", "좋음": "🟢", "보통": "🟡", "개선필요": "🔴"}
    for i, (label, score, grade) in enumerate(scores):
        with cols[i]:
            emoji = emoji_map.get(grade, "⚪")
            st.metric(f"{emoji} {label}", f"{score}점", grade)
    if pub:
        with cols[-1]:
            st.metric("📅 추천 발행", pub["best_time"], pub.get("today_score", ""))

    # 이슈/제안 표시
    issues = []
    if seo and seo.get("issues"):
        issues.extend([f"SEO: {i}" for i in seo["issues"]])
    if eng and eng.get("suggestions"):
        issues.extend([f"체류: {s}" for s in eng["suggestions"]])
    if ai and ai.get("grade") == "개선필요":
        issues.append("AI 냄새: 격식체/과장 표현 수정 필요")

    if issues:
        with st.expander(f"⚠️ 개선 포인트 {len(issues)}건", expanded=False):
            for issue in issues:
                st.caption(f"  • {issue}")
    else:
        st.caption("✅ 모든 품질 기준 통과!")


def render_blog_result():
    """블로그 생성 결과를 섹션별로 표시한다."""
    text = st.session_state.blog_result
    sections = parse_blog_sections(text)

    # 품질 리포트 (항상 보임)
    _render_quality_report(sections["body"])

    st.divider()

    # 네이버 블로그 글쓰기 버튼
    st.markdown(
        '<a href="https://blog.naver.com/GoBlogWrite.naver" target="_blank">'
        '<button style="background:#03c75a;color:white;border:none;'
        'padding:12px 24px;border-radius:8px;font-size:16px;'
        'cursor:pointer;width:100%;margin-bottom:16px;">'
        '✏️ 네이버 블로그 글쓰기 열기</button></a>',
        unsafe_allow_html=True,
    )

    # 제목 후보
    if sections["titles"]:
        st.subheader("📌 제목 후보")
        st.text_area(
            "제목 (원하는 걸 골라서 복사)",
            value=sections["titles"],
            height=120,
            key="ta_titles",
        )

    # 본문 (수정 가능)
    st.subheader("📝 본문")
    st.caption("직접 수정 가능 → '최종본 확정' 누르면 다음 글에 이 구조 반영")
    edited_body = st.text_area(
        "본문 (수정 가능)",
        value=sections["body"],
        height=500,
        key="ta_body",
    )

    # 해시태그
    hashtags = st.session_state.get("hashtags", [])
    if hashtags:
        st.subheader("🏷 해시태그")
        st.code(" ".join(hashtags), language=None)

    # 전체 복사용 (본문 + 해시태그)
    full_copy = f"{edited_body}\n\n{' '.join(hashtags)}" if hashtags else edited_body
    st.text_area(
        "📋 전체 복사 (본문 + 해시태그)",
        value=full_copy,
        height=100,
        key="ta_full_copy",
    )

    # 버튼
    if st.button("✅ 최종본 확정 (다음 글에 이 구조 반영)", use_container_width=True, key="btn_save_gold"):
        place = st.session_state.get("place_detail", {})
        name = place.get("name", "알 수 없음") if isinstance(place, dict) else "알 수 없음"
        save_gold_example(name, edited_body)
        st.success("골드 예시 저장! 다음 글에 이 구조가 반영됩니다.")
