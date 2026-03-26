"""
블로그 생성 결과 표시 모듈
제목/본문/해시태그를 섹션별로 렌더링한다.
"""

import streamlit as st

from modules.html_converter import blog_text_to_html
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

    # 본문 (텍스트 / HTML 탭)
    st.subheader("📝 본문")
    tab_text, tab_html = st.tabs(["텍스트 (일반 복사)", "HTML (서식 복사)"])
    with tab_text:
        st.text_area("본문 텍스트", value=sections["body"], height=400, key="ta_body")
    with tab_html:
        body_html = blog_text_to_html(sections["body"])
        st.markdown(
            '<p style="color:#666;font-size:13px;">'
            '📋 복사 → 네이버 에디터에 붙여넣기 → 📷 자리에 촬영 가이드 순서대로 사진 넣기</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="border:1px solid #ddd;padding:20px;border-radius:8px;'
            f'max-height:500px;overflow-y:auto;background:white;">'
            f'{body_html}</div>',
            unsafe_allow_html=True,
        )

    # 해시태그 (본문 내)
    if sections["hashtags"]:
        st.subheader("🏷 해시태그 (본문 내)")
        st.code(sections["hashtags"], language=None)
