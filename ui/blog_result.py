"""
블로그 생성 결과 표시 모듈
제목/본문/해시태그를 섹션별로 렌더링한다.
"""

import streamlit as st

from modules.gold_examples import save_gold_example
from ui.helpers import parse_blog_sections


def render_blog_result():
    """블로그 생성 결과를 섹션별로 표시한다."""
    text = st.session_state.blog_result
    sections = parse_blog_sections(text)

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

    # 본문 (수정 가능 + 복사용)
    st.subheader("📝 본문")
    st.caption("수정 후 아래 '최종본 확정' 버튼을 누르면 다음 글 생성 시 이 구조를 따라합니다")
    edited_body = st.text_area(
        "본문 (수정 가능)",
        value=sections["body"],
        height=500,
        key="ta_body",
    )

    # 버튼들
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("✅ 최종본 확정", use_container_width=True, key="btn_save_gold"):
            place = st.session_state.get("place_detail", {})
            name = place.get("name", "알 수 없음") if isinstance(place, dict) else "알 수 없음"
            save_gold_example(name, edited_body)
            st.success("골드 예시 저장! 다음 글에 이 구조가 반영됩니다.")
    with col_btn2:
        # 제목 + 본문 + 해시태그 한번에 조합
        hashtags = st.session_state.get("hashtags", [])
        titles = sections.get("titles", "")
        first_title = titles.split("\n")[0].strip() if titles else ""
        full_copy = f"{edited_body}\n\n{' '.join(hashtags)}" if hashtags else edited_body
        st.text_area(
            "📋 전체 복사용 (본문 + 해시태그)",
            value=full_copy,
            height=80,
            key="ta_full_copy",
            label_visibility="collapsed",
        )

    # 해시태그
    hashtags = st.session_state.get("hashtags")
    if hashtags:
        st.subheader("🏷 해시태그")
        st.code(" ".join(hashtags), language=None)

    # 품질 리포트 (접이식)
    seo = st.session_state.get("seo_validation")
    eng = st.session_state.get("engagement")
    pub = st.session_state.get("publish_time")
    if seo or eng:
        with st.expander("📊 품질 리포트", expanded=False):
            if seo:
                seo_emoji = {"A": "🟢", "B": "🟡", "C": "🔴"}.get(seo["grade"], "⚪")
                st.markdown(f"**SEO** {seo_emoji} {seo['score']}점 ({seo['grade']})")
                for iss in seo.get("issues", []):
                    st.caption(f"  ⚠️ {iss}")
            if eng:
                eng_emoji = {"A": "🟢", "B": "🟡", "C": "🔴"}.get(eng["grade"], "⚪")
                st.markdown(f"**체류시간** {eng_emoji} {eng['score']}점 ({eng['grade']})")
                for sug in eng.get("suggestions", []):
                    st.caption(f"  💡 {sug}")
            if pub:
                st.markdown(f"**발행 추천** {pub['best_time']} ({pub['reason']})")
