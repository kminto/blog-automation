"""
음식점 검색 모듈
사이드바 검색 UI와 검색 결과 선택을 처리한다.
네이버 글 URL에서 사진 가져오기 기능 포함.
"""

import streamlit as st

from modules.place_search import search_restaurant
from modules.place_detail import fetch_place_detail, merge_place_info
from modules.draft_reader import extract_photos_from_post, parse_blog_url
from modules.photo_analyzer import analyze_photos, extract_menus_from_analysis
from utils.api_utils import safe_api_call


def _render_draft_import():
    """네이버 글에서 사진 가져오기 UI를 렌더링한다."""
    st.markdown("---")
    st.markdown("**📥 네이버 글에서 사진 가져오기**")
    st.caption("사진만 올린 글 URL을 넣으면 자동 분석해요")

    draft_url = st.text_input(
        "글 URL",
        placeholder="https://blog.naver.com/rinx_x/123456",
        key="draft_url",
    )

    if draft_url and st.button("📥 사진 가져오기", use_container_width=True, key="btn_import_draft"):
        try:
            blog_id, log_no = parse_blog_url(draft_url)
        except ValueError as e:
            st.error(str(e))
            return

        with st.spinner("사진 추출 중..."):
            result = safe_api_call(extract_photos_from_post, blog_id, log_no)

        if not result["success"]:
            st.error(f"사진 추출 실패: {result['error']}")
            return

        photos = result["data"]
        if not photos:
            st.warning("사진을 찾을 수 없습니다. 글에 사진이 있는지 확인해주세요.")
            return

        st.success(f"📸 {len(photos)}장 추출 완료!")

        # AI 분석
        with st.spinner(f"{len(photos)}장 AI 분석 중..."):
            photo_data = [{"name": p["name"], "bytes": p["bytes"]} for p in photos]
            analysis_result = safe_api_call(analyze_photos, photo_data)

        if analysis_result["success"]:
            st.session_state["photo_analysis"] = analysis_result["data"]
            # 메뉴 자동 추출
            detected = extract_menus_from_analysis(analysis_result["data"])
            if detected:
                st.info(f"인식된 메뉴: {', '.join(detected)}")

            # 분석 결과 간단 표시
            category_icons = {
                "외관": "🏪", "내부": "🪑", "메뉴판": "📋",
                "세팅": "🥢", "메인음식": "🍽", "사이드": "🍺", "기타": "📷",
            }
            for item in analysis_result["data"]:
                cat = item.get("category", "기타")
                icon = category_icons.get(cat, "📷")
                food = f" **{item['food_name']}**" if item.get("food_name") else ""
                st.caption(f"{icon} {cat}{food}")
        else:
            st.warning(f"사진 분석 실패: {analysis_result['error']}")


def render_sidebar_search():
    """사이드바에 음식점 검색 UI를 렌더링한다."""
    st.header("🔍 음식점 검색")
    search_query = st.text_input("음식점 이름", placeholder="예: 모란돼지국밥")

    col_search, col_reset = st.columns(2)
    with col_search:
        btn_search = st.button("🔍 검색", use_container_width=True)
    with col_reset:
        btn_reset = st.button("🔄 초기화", use_container_width=True)

    # 네이버 글에서 사진 가져오기
    _render_draft_import()

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
