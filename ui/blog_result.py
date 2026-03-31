"""
블로그 생성 결과 표시 모듈
제목/본문/해시태그를 섹션별로 렌더링한다.
"""

import streamlit as st

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

    # 본문 (네이버 에디터 붙여넣기용)
    st.subheader("📝 본문")
    st.caption("전체 선택(Ctrl+A) → 복사(Ctrl+C) → 네이버 에디터에 붙여넣기")
    st.text_area(
        "본문 (복사용)",
        value=sections["body"],
        height=500,
        key="ta_body",
    )

    # 해시태그 (generate_hashtags 결과만 사용, 본문 내 해시태그와 중복 제거)
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
