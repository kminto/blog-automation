"""
음식점 상세 정보 및 입력 폼 모듈
심플한 1페이지: 입력 → 버튼 → 결과. 탭/전환 없음.
"""

import streamlit as st

from modules.validators import parse_comma_separated
from modules.place_search import extract_region_from_address, extract_menus_from_category
from modules.place_detail import fetch_place_detail
from ui.helpers import build_my_review, build_auto_memo


def _build_detailed_review_from_form() -> dict:
    """세분화 후기 폼에서 detailed_review 딕셔너리를 조립한다."""
    review = {}

    sd = {}
    for key in ["sd_items", "sd_taste", "sd_refill", "sd_highlight"]:
        val = st.session_state.get(key, "")
        if val:
            sd[key.replace("sd_", "")] = val
    if sd:
        review["side_dishes"] = sd

    sv = {}
    for key in ["sv_staff", "sv_extras"]:
        val = st.session_state.get(key, "")
        if val:
            sv[key.replace("sv_", "")] = val
    if sv:
        review["service"] = sv

    for key in ["pr_eval", "pr_complaints", "pr_revisit", "pr_recommend"]:
        val = st.session_state.get(key, "")
        if val:
            field_map = {"pr_eval": "price_eval", "pr_complaints": "complaints",
                         "pr_revisit": "revisit", "pr_recommend": "recommend_to"}
            review[field_map[key]] = val

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
    """심플한 1페이지 UI: 음식점 정보 → 입력 → 버튼 → 결과."""
    info = st.session_state.place_detail

    # 시설 정보가 없으면 자동 보충 (기존 글 호환)
    if not info.get("parking_details") and not info.get("restroom_info") and info.get("name"):
        updated = fetch_place_detail(name=info["name"])
        if updated:
            info.update(updated)
            st.session_state.place_detail = info

    # === 헤더: 음식점명 + 최신정보 + 생성 버튼 ===
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
                for key, val in {
                    "input_parking": " / ".join(updated.get("parking_details", [])),
                    "input_restroom": " / ".join(updated.get("restroom_info", [])),
                    "input_access": " / ".join(updated.get("access_info", [])),
                    "input_facilities": " / ".join(updated.get("facilities_info", [])),
                }.items():
                    if val:
                        st.session_state[key] = val
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

    st.divider()

    # === 입력 영역 (생성 후에는 접이식) ===
    has_result = st.session_state.get("blog_result") is not None
    input_label = "✏️ 입력 (수정하려면 펼치세요)" if has_result else "✏️ 입력"

    with st.expander(input_label, expanded=not has_result):
        # 지역/메뉴
        auto_regions = extract_region_from_address(
            info.get("road_address", ""), jibun_address=info.get("address", ""),
        )
        auto_menus = info.get("menus", [])
        if not auto_menus:
            auto_menus = extract_menus_from_category(info.get("category", ""))

        col_r, col_m = st.columns(2)
        with col_r:
            regions = st.text_input("지역", value=", ".join(auto_regions), key="input_regions")
        with col_m:
            menus = st.text_input("메뉴", value=", ".join(auto_menus[:5]), key="input_menus")

        # 필수: 메뉴 후기
        ordered_menus = st.text_area(
            "🍽 주문 메뉴 - 한줄평 *",
            placeholder="팟타이 - 면 쫄깃\n똠양꿍 - 국물 시원",
            height=80, key="input_ordered",
        )

        # 서론/결론 한 줄씩
        col1, col2, col3 = st.columns(3)
        with col1:
            visit_reason = st.text_input("🚶 방문 계기", placeholder="친구 추천", key="input_visit_reason")
        with col2:
            companion = st.text_input("👫 동행", placeholder="친구", key="input_companion")
        with col3:
            mood = st.text_input("✨ 분위기", placeholder="깔끔", key="input_mood")

        # 매장 정보 (자동 수집)
        with st.expander("🏪 매장 · 시설 (자동 수집됨)", expanded=False):
            auto_p = " / ".join(info.get("parking_details", []))
            auto_r = " / ".join(info.get("restroom_info", []))
            auto_a = " / ".join(info.get("access_info", []))
            auto_f = " / ".join(info.get("facilities_info", []))

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.text_input("🅿️ 주차", value=st.session_state.get("input_parking") or auto_p, key="input_parking")
                st.text_input("🚇 접근성", value=st.session_state.get("input_access") or auto_a, key="input_access")
            with col_f2:
                st.text_input("🚻 화장실", value=st.session_state.get("input_restroom") or auto_r, key="input_restroom")
                st.text_input("🪑 편의시설", value=st.session_state.get("input_facilities") or auto_f, key="input_facilities")

        # 세분화 후기
        with st.expander("📋 세분화 후기 (선택)", expanded=False):
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.text_input("🥢 반찬 종류", placeholder="갈치속젓, 콩나물", key="sd_items")
                st.text_input("⭐ 맛있었던 반찬", placeholder="갈치속젓 최고", key="sd_highlight")
                st.text_input("🍳 직원 평가", placeholder="친절", key="sv_staff")
                st.text_input("💰 가격", placeholder="1인 45,000원", key="pr_eval")
            with col_d2:
                st.text_input("📝 반찬 평가", placeholder="정성스러움", key="sd_taste")
                st.text_input("🔄 리필", placeholder="리필 가능", key="sd_refill")
                st.text_input("🎁 서비스", placeholder="직접 잘라줌", key="sv_extras")
                st.text_input("👎 아쉬운 점", placeholder="가격 있는 편", key="pr_complaints")

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.text_input("🔁 재방문", placeholder="100%", key="pr_revisit")
            with col_p2:
                st.text_input("👥 추천 대상", placeholder="가족, 회식", key="pr_recommend")

        # 메모
        memo = st.text_area("📝 메모 (선택)", value=build_auto_memo(info), height=50, key="input_memo")

    # === 🚀 생성 버튼 (입력 바로 아래) ===
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
            # 빠른선택/세분화 조립
            detailed_review = _build_detailed_review_from_form()

            mood_parts = [st.session_state.get("input_mood", "")]
            for key, label in [("input_parking", "주차"), ("input_access", "접근성"),
                               ("input_restroom", "화장실"), ("input_facilities", "편의시설")]:
                val = st.session_state.get(key, "")
                if val and val.strip():
                    mood_parts.append(f"{label}: {val}")
            full_mood = ", ".join([p for p in mood_parts if p])

            on_generate(
                info["name"], region_list, menu_list,
                st.session_state.get("input_companion", ""),
                full_mood,
                st.session_state.get("input_memo", ""),
                st.session_state.get("input_ordered", ""),
                "",  # my_review
                None,  # photos
                detailed_review=detailed_review,
                visit_reason=st.session_state.get("input_visit_reason", ""),
            )
