"""
인증 모듈
비밀번호 잠금 화면을 처리한다.
"""

import streamlit as st


def check_authentication() -> bool:
    """비밀번호 인증을 확인한다. 인증되지 않으면 로그인 화면을 표시하고 False를 반환한다."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.markdown("#### 🔒 로그인")
    pw = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if pw == st.secrets.get("APP_PASSWORD", ""):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    return False
