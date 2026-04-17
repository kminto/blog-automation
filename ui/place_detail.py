"""
음식점 상세 정보 및 입력 폼 모듈
블로그 흐름(서론→매장→음식→총평) 순서로 키워드만 간단히 입력.
"""

import streamlit as st

from modules.validators import parse_comma_separated
from modules.place_search import extract_region_from_address, extract_menus_from_category
from modules.place_detail import fetch_place_detail
from ui.helpers import build_auto_memo


def _auto_value(session_key: str, fallback: str) -> str:
    """세션에 값이 있으면 세션값, 없으면 fallback(자동수집값)."""
    val = st.session_state.get(session_key)
    if val and val.strip():
        return val
    return fallback


def _build_detailed_review_from_form() -> dict:
    """입력 폼에서 detailed_review 딕셔너리를 조립한다."""
    review = {}

    # 반찬
    sd = {}
    for key in ["sd_items", "sd_taste"]:
        val = st.session_state.get(key, "")
        if val:
            sd[key.replace("sd_", "")] = val
    if sd:
        review["side_dishes"] = sd

    # 서비스
    sv_staff = st.session_state.get("sv_staff", "")
    if sv_staff:
        review["service"] = {"staff": sv_staff}

    # 가격/재방문/추천
    for key in ["pr_eval", "pr_complaints", "pr_revisit", "pr_recommend"]:
        val = st.session_state.get(key, "")
        if val:
            field_map = {
                "pr_eval": "price_eval", "pr_complaints": "complaints",
                "pr_revisit": "revisit", "pr_recommend": "recommend_to",
            }
            review[field_map[key]] = val

    # 메뉴별 한줄평
    ordered = st.session_state.get("input_ordered", "")
    if ordered and ordered.strip():
        menu_reviews = []
        for line in ordered.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split(" - ", 1)
            mr = {"name": parts[0].strip()}
            if len(parts) > 1:
                mr["one_liner"] = parts[1].strip()
            menu_reviews.append(mr)
        if menu_reviews:
            review["menu_reviews"] = menu_reviews

    return review if review else None


def render_place_detail(on_analyze, on_generate):
    """블로그 흐름 순서대로 입력하는 1페이지 UI."""
    info = st.session_state.place_detail

    # 시설 정보 자동 보충
    if not info.get("parking_details") and not info.get("restroom_info") and info.get("name"):
        updated = fetch_place_detail(name=info["name"])
        if updated:
            info.update(updated)
            st.session_state.place_detail = info

    # === 헤더 ===
    col_name, col_refresh = st.columns([5, 1])
    with col_name:
        st.subheader(f"🏪 {info['name']}")
    with col_refresh:
        if st.button("🔄", key="btn_refresh", help="최신 정보 다시 가져오기"):
            with st.spinner("조회 중..."):
                updated = fetch_place_detail(name=info.get("name", ""))
            if updated:
                info.update(updated)
                st.session_state.place_detail = info
                st.rerun()

    # 기본 정보 1줄
    addr = info.get("road_address") or info.get("address", "")
    info_parts = [f"📍 {addr}"] if addr else []
    if info.get("business_hours"):
        info_parts.append(f"🕐 {info['business_hours']}")
    if info.get("telephone"):
        info_parts.append(f"📞 {info['telephone']}")
    if info_parts:
        st.caption(" · ".join(info_parts))

    # 지역/메뉴 (숨김)
    auto_regions = extract_region_from_address(
        info.get("road_address", ""), jibun_address=info.get("address", ""),
    )
    auto_menus = info.get("menus", [])
    if not auto_menus:
        auto_menus = extract_menus_from_category(info.get("category", ""))

    with st.expander("🏷 지역 · 메뉴 키워드", expanded=False):
        col_r, col_m = st.columns(2)
        with col_r:
            st.text_input("지역", value=", ".join(auto_regions), key="input_regions")
        with col_m:
            st.text_input("메뉴", value=", ".join(auto_menus[:5]), key="input_menus")

    st.divider()

    # === 입력 영역 (블로그 흐름 순서) ===
    has_result = st.session_state.get("blog_result") is not None
    input_label = "✏️ 블로그 입력 (수정하려면 펼치세요)" if has_result else "✏️ 블로그 입력"

    with st.expander(input_label, expanded=not has_result):

        # ── 📌 서론 ──
        st.markdown("**📌 서론**")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.text_input(
                "누구와?",
                placeholder="친구, 가족, 혼밥",
                key="input_companion",
            )
        with col_s2:
            st.text_input(
                "방문 계기",
                placeholder="인스타 추천, 지인 소개",
                key="input_visit_reason",
            )

        # ── 📍 매장 ──
        st.markdown("**📍 매장**")

        # 자동채움 값 준비
        auto_access = " / ".join(info.get("access_info", []))
        auto_parking = " / ".join(info.get("parking_details", []))
        auto_restroom = " / ".join(info.get("restroom_info", []))
        auto_facilities = " / ".join(info.get("facilities_info", []))

        st.text_input(
            "접근성",
            value=_auto_value("input_access", auto_access),
            placeholder="역에서 도보 3분",
            key="input_access",
        )
        st.text_input(
            "외관",
            placeholder="간판 큼, 1층 코너",
            key="input_exterior",
        )
        st.text_input(
            "주차",
            value=_auto_value("input_parking", auto_parking),
            placeholder="건물 주차 가능",
            key="input_parking",
        )
        st.text_input(
            "내부 분위기",
            placeholder="넓음, 깔끔, 테이블 간격 넉넉",
            key="input_mood",
        )
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.text_input(
                "화장실",
                value=_auto_value("input_restroom", auto_restroom),
                placeholder="매장 내부, 깨끗",
                key="input_restroom",
            )
        with col_f2:
            st.text_input(
                "편의시설",
                value=_auto_value("input_facilities", auto_facilities),
                placeholder="유아의자, 콘센트",
                key="input_facilities",
            )

        # ── 🍽 음식 ──
        st.markdown("**🍽 음식**")
        st.text_input(
            "기본반찬",
            placeholder="김치, 콩나물, 계란찜",
            key="sd_items",
        )
        st.text_area(
            "주문 메뉴 · 한줄평 *",
            placeholder="팟타이 - 면 쫄깃\n똠양꿍 - 국물 시원",
            height=80,
            key="input_ordered",
        )
        st.text_input(
            "사이드 · 추천 메뉴 (선택)",
            placeholder="볶음밥, 디저트",
            key="input_side_menu",
        )
        st.text_input(
            "맛 평가",
            placeholder="전체적으로 간이 딱, 소스 특이",
            key="sd_taste",
        )

        # ── ⭐ 총평 ──
        st.markdown("**⭐ 총평**")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.text_input(
                "재방문 의사",
                placeholder="100% 재방문",
                key="pr_revisit",
            )
        with col_t2:
            st.text_input(
                "추천 대상 · 이유",
                placeholder="데이트, 가족 모임",
                key="pr_recommend",
            )
        st.text_input(
            "아쉬운 점 (선택)",
            placeholder="웨이팅 길어요, 가격 있는 편",
            key="pr_complaints",
        )

    # === 🚀 생성 버튼 ===
    btn_generate = st.button(
        "🚀 키워드 분석 + 본문 생성",
        use_container_width=True,
        type="primary",
        key="btn_full_pipeline",
    )

    # === 생성 실행 ===
    if btn_generate:
        region_list = parse_comma_separated(st.session_state.get("input_regions", ""))
        menu_list = parse_comma_separated(st.session_state.get("input_menus", ""))
        if not region_list or not menu_list:
            st.error("지역과 메뉴를 최소 하나씩 입력해주세요.")
        else:
            detailed_review = _build_detailed_review_from_form()

            # 매장 정보를 memo에 자동 조합
            memo = build_auto_memo(info)

            # 매장 입력 키워드를 mood에 조합
            mood_parts = []
            for key, label in [
                ("input_mood", "분위기"), ("input_exterior", "외관"),
                ("input_parking", "주차"), ("input_access", "접근성"),
                ("input_restroom", "화장실"), ("input_facilities", "편의시설"),
            ]:
                val = st.session_state.get(key, "")
                if val and val.strip():
                    mood_parts.append(f"{label}: {val}")
            full_mood = ", ".join(mood_parts)

            # 사이드 메뉴를 ordered에 추가
            ordered = st.session_state.get("input_ordered", "")
            side = st.session_state.get("input_side_menu", "")
            if side and side.strip():
                ordered += f"\n{side.strip()} - 사이드"

            on_generate(
                info["name"], region_list, menu_list,
                st.session_state.get("input_companion", ""),
                full_mood,
                memo,
                ordered,
                "",  # my_review
                None,  # photos
                detailed_review=detailed_review,
                visit_reason=st.session_state.get("input_visit_reason", ""),
            )
