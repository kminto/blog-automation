"""
블로그 생성 결과 표시 모듈
제목/본문/해시태그를 섹션별로 렌더링하고, 자동 포스팅 기능을 제공한다.
"""

import os

import streamlit as st

from modules.html_converter import blog_text_to_html
from modules.blog_poster import check_selenium_available, auto_post
from ui.helpers import parse_blog_sections


def _render_auto_post_section(sections: dict):
    """자동 포스팅 섹션을 렌더링한다."""
    if not check_selenium_available():
        st.caption("⚠️ 자동 포스팅을 사용하려면: `pip install selenium undetected-chromedriver pyperclip`")
        return

    st.markdown("---")
    st.subheader("🤖 네이버 블로그 자동 포스팅")
    st.caption("⚠️ 임시저장까지만 자동화됩니다. 최종 발행은 브라우저에서 직접 확인 후 진행하세요.")

    # 제목 선택
    title_lines = [l.strip() for l in sections["titles"].split("\n") if l.strip()]
    selected_title = st.selectbox(
        "발행할 제목 선택",
        title_lines if title_lines else ["제목 없음"],
        key="auto_post_title",
    )

    # 네이버 계정 (세션에 저장)
    col1, col2 = st.columns(2)
    with col1:
        naver_id = st.text_input(
            "네이버 ID",
            value=st.session_state.get("naver_id", ""),
            key="input_naver_id",
        )
    with col2:
        naver_pw = st.text_input(
            "네이버 PW",
            type="password",
            key="input_naver_pw",
        )

    blog_id = st.text_input(
        "블로그 ID",
        value="rinx_x",
        key="input_blog_id",
    )

    # 사진 포함 여부
    has_photos = st.session_state.get("photo_upload") and len(st.session_state["photo_upload"]) > 0
    include_photos = False
    if has_photos:
        include_photos = st.checkbox(
            f"📸 업로드한 사진 {len(st.session_state['photo_upload'])}장도 함께 올리기",
            value=True,
            key="include_photos",
        )

    if st.button("🚀 네이버 블로그에 임시저장", use_container_width=True, key="btn_auto_post"):
        if not naver_id or not naver_pw:
            st.error("네이버 ID와 PW를 입력해주세요.")
            return

        # ID 세션 저장 (PW는 저장 안 함)
        st.session_state["naver_id"] = naver_id

        # 사진 데이터 준비
        photo_files = None
        if include_photos and has_photos:
            photo_files = []
            for f in st.session_state["photo_upload"]:
                f.seek(0)
                photo_files.append({"name": f.name, "bytes": f.read()})

        with st.spinner("🤖 네이버 블로그에 접속 중... (30~60초 소요)"):
            result = auto_post(
                blog_id=blog_id,
                naver_id=naver_id,
                naver_pw=naver_pw,
                title=selected_title,
                body_text=sections["body"],
                photo_files=photo_files,
                publish=False,
            )

        if result["success"]:
            st.success(result["message"])
            st.info("브라우저 창이 열려 있습니다. 내용 확인 후 '발행' 버튼을 누르세요.")
        else:
            st.error(result["message"])


def render_blog_result():
    """블로그 생성 결과를 섹션별로 표시한다."""
    text = st.session_state.blog_result
    sections = parse_blog_sections(text)

    # 네이버 블로그 글쓰기 버튼 (수동)
    st.markdown(
        '<a href="https://blog.naver.com/GoBlogWrite.naver" target="_blank">'
        '<button style="background:#03c75a;color:white;border:none;'
        'padding:12px 24px;border-radius:8px;font-size:16px;'
        'cursor:pointer;width:100%;margin-bottom:16px;">'
        '✏️ 네이버 블로그 글쓰기 열기 (수동)</button></a>',
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
            '📋 복사 → 네이버 에디터에 붙여넣기</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="border:1px solid #ddd;padding:20px;border-radius:8px;'
            f'max-height:500px;overflow-y:auto;background:white;">'
            f'{body_html}</div>',
            unsafe_allow_html=True,
        )

    # 해시태그
    if sections["hashtags"]:
        st.subheader("🏷 해시태그")
        st.code(sections["hashtags"], language=None)

    # 자동 포스팅 섹션
    _render_auto_post_section(sections)
