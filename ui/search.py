"""
음식점 검색 모듈
사이드바 검색 UI와 검색 결과 선택을 처리한다.
"""

import streamlit as st

from modules.place_search import search_restaurant
from modules.place_detail import fetch_place_detail, merge_place_info
from utils.api_utils import safe_api_call


def render_sidebar_search():
    """사이드바에 음식점 검색 UI를 렌더링한다. (btn_search, btn_reset) 튜플을 반환한다."""
    st.header("🔍 음식점 검색")
    search_query = st.text_input("음식점 이름", placeholder="예: 모란돼지국밥")

    col_search, col_reset = st.columns(2)
    with col_search:
        btn_search = st.button("🔍 검색", use_container_width=True)
    with col_reset:
        btn_reset = st.button("🔄 초기화", use_container_width=True)

    return search_query, btn_search, btn_reset


def handle_reset():
    """세션 상태를 초기화한다."""
    for key in [
        "keyword_results", "scored_keywords", "blog_result",
        "hashtags", "search_results", "selected_place", "place_detail",
    ]:
        st.session_state[key] = None
    st.rerun()


def handle_search(query: str):
    """음식점 검색을 실행한다."""
    with st.spinner("음식점 검색 중..."):
        result = safe_api_call(search_restaurant, query)
        if result["success"] and result["data"]:
            st.session_state.search_results = result["data"]
            st.session_state.selected_place = None
            st.session_state.place_detail = None
        else:
            st.error(f"검색 실패: {result.get('error', '결과가 없습니다.')}")


def render_search_results():
    """검색 결과를 표시하고 선택을 처리한다."""
    st.subheader("📍 검색 결과 - 음식점을 선택하세요")
    for idx, place in enumerate(st.session_state.search_results):
        col_info, col_btn = st.columns([4, 1])
        with col_info:
            st.markdown(f"**{place['title']}**")
            st.caption(
                f"📍 {place['road_address'] or place['address']} "
                f"| 📂 {place['category']} "
                f"| 📞 {place['telephone'] or '정보 없음'}"
            )
        with col_btn:
            if st.button("선택", key=f"select_{idx}"):
                st.session_state.selected_place = place
                with st.spinner("상세 정보 수집 중..."):
                    detail = fetch_place_detail(
                        place.get("link", ""),
                        name=place.get("title", ""),
                        address=place.get("road_address", ""),
                    )
                    merged = merge_place_info(place, detail)
                    st.session_state.place_detail = merged
                st.rerun()
        st.divider()
