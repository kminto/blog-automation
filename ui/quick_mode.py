"""
퀵 모드 UI 모듈
음식점명 + 메모 3줄만 입력하면 블로그 글 자동 생성.
"""

import streamlit as st

from modules.memo_parser import parse_quick_memo
from modules.place_detail import fetch_place_detail
from modules.place_search import extract_region_from_address, extract_menus_from_category
from modules.pipeline import run_full_pipeline
from utils.api_utils import safe_api_call


def render_quick_mode():
    """퀵 모드 UI를 렌더링한다."""
    st.markdown("#### 퀵 모드")
    st.caption("음식점명 + 메모만 적으면 끝! 1~2분 안에 블로그 글 완성")

    restaurant_name = st.text_input(
        "음식점명",
        placeholder="다현목포갯벌산낙지",
        key="quick_name",
    )

    memo_text = st.text_area(
        "메모 (자유롭게)",
        placeholder="산낙지볶음 맵게, 공기밥 필수. 연포탕 사장님이 직접 넣어줌.\n"
                    "갈치속젓 리필됨. 부모님과 감. 친절함. 가격 좀 있음.\n"
                    "다음엔 산낙지회 먹어볼 예정",
        height=120,
        key="quick_memo",
    )

    btn = st.button(
        "퀵 생성",
        use_container_width=True,
        type="primary",
        key="btn_quick_generate",
    )

    # 이전 파싱 결과 미리보기
    if st.session_state.get("quick_parsed"):
        _render_parsed_preview(st.session_state["quick_parsed"])

    if btn:
        if not restaurant_name or not restaurant_name.strip():
            st.error("음식점명을 입력해주세요.")
            return
        if not memo_text or not memo_text.strip():
            st.error("메모를 최소 한 줄은 입력해주세요.")
            return

        _run_quick_pipeline(restaurant_name.strip(), memo_text.strip())


def _run_quick_pipeline(restaurant_name: str, memo_text: str):
    """퀵 모드 파이프라인을 실행한다."""
    progress = st.progress(0)
    status = st.status("퀵 모드 시작...", expanded=True)

    # 1. 운영정보 수집
    status.update(label="운영정보 수집 중...")
    place_detail = fetch_place_detail(name=restaurant_name)
    if place_detail:
        addr = place_detail.get("road_address", "")
        hours = place_detail.get("business_hours", "미확인")
        status.write(f"주소: {addr}")
        status.write(f"영업시간: {hours}")
    else:
        place_detail = {}
        status.write("운영정보 수집 실패 — 메모 기반으로 진행")
    progress.progress(10)

    # 2. 지역 추출
    region_list = extract_region_from_address(
        place_detail.get("road_address", ""),
        jibun_address=place_detail.get("address", ""),
    )
    if not region_list:
        region_list = [restaurant_name.split()[0]] if " " in restaurant_name else []
    status.write(f"지역: {', '.join(region_list)}")
    progress.progress(15)

    # 3. 메모 파싱
    status.update(label="메모 파싱 중... (3~5초)")
    parsed_result = safe_api_call(parse_quick_memo, restaurant_name, memo_text)
    if not parsed_result["success"]:
        status.write(f"메모 파싱 실패: {parsed_result['error']}")
        parsed = {"menus": [], "companion": "", "mood": "", "ordered_menus": memo_text, "detailed_review": None}
    else:
        parsed = parsed_result["data"]
    st.session_state["quick_parsed"] = parsed
    progress.progress(25)

    # 파싱 결과 표시
    menus_str = ", ".join(parsed.get("menus", []))
    companion = parsed.get("companion", "")
    status.write(f"메뉴: {menus_str or '미감지'}")
    status.write(f"동행: {companion or '미감지'}")

    # 4. 메뉴 리스트 조합
    menu_list = parsed.get("menus", [])
    place_menus = place_detail.get("menus", [])
    if not place_menus:
        place_menus = extract_menus_from_category(place_detail.get("category", ""))
    # 파싱 메뉴 우선, place 메뉴로 보충
    seen = set(menu_list)
    for m in place_menus:
        if m not in seen:
            menu_list.append(m)
            seen.add(m)

    if not menu_list:
        menu_list = [restaurant_name]

    # 5. 파이프라인 실행
    status.update(label="키워드 분석 + 본문 생성 중...")
    st.session_state["place_detail"] = place_detail

    run_full_pipeline(
        restaurant_name=restaurant_name,
        region_list=region_list,
        menu_list=menu_list,
        companion=companion,
        mood=parsed.get("mood", ""),
        memo=memo_text,
        ordered_menus=parsed.get("ordered_menus", ""),
        my_review="",
        uploaded_photos=None,
        place_detail=place_detail,
        detailed_review=parsed.get("detailed_review"),
    )


def _render_parsed_preview(parsed: dict):
    """파싱 결과 미리보기를 렌더링한다."""
    with st.expander("파싱 결과 미리보기", expanded=False):
        cols = st.columns(2)
        with cols[0]:
            st.markdown(f"**메뉴:** {', '.join(parsed.get('menus', [])) or '미감지'}")
            st.markdown(f"**동행:** {parsed.get('companion', '') or '미감지'}")
            st.markdown(f"**분위기:** {parsed.get('mood', '') or '미감지'}")
        with cols[1]:
            dr = parsed.get("detailed_review", {}) or {}
            sv = dr.get("service", {})
            st.markdown(f"**서비스:** {sv.get('staff', '') or '미감지'}")
            st.markdown(f"**가격:** {dr.get('price_eval', '') or '미감지'}")
            st.markdown(f"**재방문:** {dr.get('revisit', '') or '미감지'}")
