"""
음식점 상세 정보 및 입력 폼 모듈
입력 탭 / 결과 탭 분리. 필수 최소 입력 → 버튼 1번 → 완료.
"""

import streamlit as st

from modules.validators import parse_comma_separated
from modules.place_search import extract_region_from_address, extract_menus_from_category
from modules.place_detail import fetch_place_detail
from ui.helpers import build_my_review, build_auto_memo


def _build_detailed_review_from_form() -> dict:
    """Streamlit 세분화 후기 폼에서 detailed_review 딕셔너리를 조립한다."""
    review = {}

    sd = {}
    if st.session_state.get("sd_items"):
        sd["items"] = st.session_state["sd_items"]
    if st.session_state.get("sd_taste"):
        sd["taste"] = st.session_state["sd_taste"]
    if st.session_state.get("sd_refill"):
        sd["refill"] = st.session_state["sd_refill"]
    if st.session_state.get("sd_highlight"):
        sd["highlight"] = st.session_state["sd_highlight"]
    if sd:
        review["side_dishes"] = sd

    sv = {}
    if st.session_state.get("sv_staff"):
        sv["staff"] = st.session_state["sv_staff"]
    if st.session_state.get("sv_extras"):
        sv["extras"] = st.session_state["sv_extras"]
    if sv:
        review["service"] = sv

    if st.session_state.get("pr_eval"):
        review["price_eval"] = st.session_state["pr_eval"]
    if st.session_state.get("pr_complaints"):
        review["complaints"] = st.session_state["pr_complaints"]
    if st.session_state.get("pr_revisit"):
        review["revisit"] = st.session_state["pr_revisit"]
    if st.session_state.get("pr_recommend"):
        review["recommend_to"] = st.session_state["pr_recommend"]

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


def _render_store_info(info: dict):
    """음식점 기본 정보를 컴팩트하게 표시한다."""
    # 상세 도로명 주소 우선 (층수/호수 포함)
    addr = info.get("road_address", "") or info.get("address", "")
    hours = info.get("business_hours", "")
    tel = info.get("telephone", "")
    category = info.get("category", "")

    line1 = []
    if addr:
        line1.append(f"📍 {addr}")
    if category:
        line1.append(f"📂 {category}")
    if line1:
        st.caption(" · ".join(line1))

    line2 = []
    if hours:
        line2.append(f"🕐 {hours}")
    if tel:
        line2.append(f"📞 {tel}")
    if info.get("parking"):
        line2.append(f"🅿️ {info['parking']}")
    if line2:
        st.caption(" · ".join(line2))


def _render_input_tab(info: dict, auto_regions: list, auto_menus: list):
    """입력 탭을 렌더링한다."""

    # --- 필수 입력 ---
    st.markdown("#### ✏️ 필수 입력")

    regions = st.text_input("지역 (쉼표 구분)", value=", ".join(auto_regions), key="input_regions")
    menus = st.text_input("대표 메뉴 (쉼표 구분)", value=", ".join(auto_menus[:5]), key="input_menus")

    ordered_menus = st.text_area(
        "🍽 주문한 메뉴 - 한줄평 *",
        placeholder="팟타이 - 면 쫄깃, 새우 탱글\n똠양꿍 - 국물 시원, 매콤",
        height=100,
        key="input_ordered",
    )

    col1, col2 = st.columns(2)
    with col1:
        visit_reason = st.text_input("🚶 방문 계기", placeholder="친구 추천 / 검색", key="input_visit_reason")
    with col2:
        companion = st.text_input("👫 동행", placeholder="친구, 부모님", key="input_companion")

    st.divider()

    # --- 선택 입력 (접이식) ---
    with st.expander("🏪 매장 정보 (선택 — 자동 수집됨)", expanded=False):
        mood = st.text_input("✨ 분위기", placeholder="깔끔, 넓은 테이블", key="input_mood")

        auto_parking = " / ".join(info.get("parking_details", []))
        auto_restroom = " / ".join(info.get("restroom_info", []))
        auto_access = " / ".join(info.get("access_info", []))
        auto_facilities = " / ".join(info.get("facilities_info", []))

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            parking_info = st.text_input(
                "🅿️ 주차", key="input_parking",
                value=st.session_state.get("input_parking") or auto_parking,
            )
            access_info = st.text_input(
                "🚇 접근성", key="input_access",
                value=st.session_state.get("input_access") or auto_access,
            )
        with col_m2:
            restroom = st.text_input(
                "🚻 화장실", key="input_restroom",
                value=st.session_state.get("input_restroom") or auto_restroom,
            )
            facilities = st.text_input(
                "🪑 편의시설", key="input_facilities",
                value=st.session_state.get("input_facilities") or auto_facilities,
            )

    with st.expander("🍽 세분화 후기 (선택 — 더 정확한 글)", expanded=False):
        col_sd1, col_sd2 = st.columns(2)
        with col_sd1:
            st.text_input("🥢 반찬 종류", placeholder="갈치속젓, 알배추, 콩나물", key="sd_items")
            st.text_input("⭐ 맛있었던 반찬", placeholder="갈치속젓 감칠맛 최고", key="sd_highlight")
            st.text_input("🍳 사장님/직원", placeholder="매우 친절", key="sv_staff")
        with col_sd2:
            st.text_input("📝 반찬 평가", placeholder="정성스러움", key="sd_taste")
            st.text_input("🔄 리필 여부", placeholder="갈치속젓 리필 가능", key="sd_refill")
            st.text_input("🎁 서비스/특이사항", placeholder="직접 잘라줌", key="sv_extras")

        col_pr1, col_pr2 = st.columns(2)
        with col_pr1:
            st.text_input("💰 가격 평가", placeholder="1인 45,000원. 납득 가능", key="pr_eval")
            st.text_input("👎 아쉬운 점", placeholder="가격 좀 있는 편", key="pr_complaints")
        with col_pr2:
            st.text_input("🔁 재방문 의사", placeholder="100%, 다음엔 산낙지회", key="pr_revisit")
            st.text_input("👥 추천 대상", placeholder="부모님, 가족, 회식", key="pr_recommend")

    with st.expander("📋 빠른 선택 (선택)", expanded=False):
        col_v1, col_v2 = st.columns(2)
        vibe_options = ["가성비 좋음", "고급짐/특별한 날", "양 많음", "맛은 좋은데 비쌈",
                        "동네 단골각", "데이트 맛집", "가족모임 적합", "혼밥 가능"]
        vibe_selected = []
        for i, opt in enumerate(vibe_options):
            col = col_v1 if i % 2 == 0 else col_v2
            with col:
                if st.checkbox(opt, key=f"vibe_{i}"):
                    vibe_selected.append(opt)

        cook_options = ["직원이 구워줌", "내가 직접 구움", "이미 조리돼서 나옴", "셰프가 눈앞에서 조리"]
        review_cook = ""
        for opt in cook_options:
            if st.checkbox(opt, key=f"cook_{opt}"):
                review_cook = opt

        col_w1, col_w2 = st.columns(2)
        with col_w1:
            wait_options = ["웨이팅 없음", "5~10분 대기", "10~30분 대기", "예약 입장"]
            review_wait = ""
            for opt in wait_options:
                if st.checkbox(opt, key=f"wait_{opt}"):
                    review_wait = opt
        with col_w2:
            revisit_options = ["무조건 재방문", "가끔 올만함", "한번은 갈만함", "비추"]
            review_revisit = ""
            for opt in revisit_options:
                if st.checkbox(opt, key=f"revisit_{opt}"):
                    review_revisit = opt

    review_vibe = ", ".join(vibe_selected) if vibe_selected else ""
    review_best = st.session_state.get("review_best", "")
    memo = st.text_area("📝 추가 메모 (선택)", value=build_auto_memo(info), height=60, key="input_memo")

    # 값 반환용 세션 저장
    st.session_state["_form_data"] = {
        "regions": regions, "menus": menus, "ordered_menus": ordered_menus,
        "visit_reason": visit_reason, "companion": companion,
        "mood": st.session_state.get("input_mood", ""),
        "parking_info": st.session_state.get("input_parking", ""),
        "access_info": st.session_state.get("input_access", ""),
        "restroom": st.session_state.get("input_restroom", ""),
        "facilities": st.session_state.get("input_facilities", ""),
        "review_vibe": review_vibe, "review_cook": review_cook,
        "review_wait": review_wait, "review_revisit": review_revisit,
        "memo": memo,
    }


def render_place_detail(on_analyze, on_generate):
    """음식점 상세 + 입력 폼 + 생성 버튼을 렌더링한다."""
    info = st.session_state.place_detail

    # 음식점명 + 기본 정보 (컴팩트)
    col_title, col_refresh = st.columns([4, 1])
    with col_title:
        st.subheader(f"🏪 {info['name']}")
    with col_refresh:
        if st.button("🔄 최신정보", key="btn_refresh_info"):
            with st.spinner("조회 중..."):
                updated = fetch_place_detail(name=info.get("name", ""))
            if updated:
                info.update(updated)
                st.session_state.place_detail = info
                # 입력란 세션값도 새 정보로 갱신 (빈 값 덮어쓰기)
                auto_map = {
                    "input_parking": " / ".join(updated.get("parking_details", [])),
                    "input_restroom": " / ".join(updated.get("restroom_info", [])),
                    "input_access": " / ".join(updated.get("access_info", [])),
                    "input_facilities": " / ".join(updated.get("facilities_info", [])),
                }
                for key, val in auto_map.items():
                    if val:  # 새 값이 있으면 덮어쓰기
                        st.session_state[key] = val
                st.success("최신 정보 업데이트!")
                st.rerun()

    _render_store_info(info)

    # 🚀 생성 버튼 (상단 고정)
    btn_generate = st.button(
        "🚀 키워드 분석 + 본문 생성",
        use_container_width=True,
        type="primary",
        key="btn_full_pipeline",
    )

    # 지역/메뉴 자동 추출
    auto_regions = extract_region_from_address(
        info.get("road_address", ""),
        jibun_address=info.get("address", ""),
    )
    auto_menus = info.get("menus", [])
    if not auto_menus:
        auto_menus = extract_menus_from_category(info.get("category", ""))

    # 결과가 있으면 결과 탭이 기본, 없으면 입력 탭이 기본
    has_result = st.session_state.get("blog_result") is not None

    if has_result:
        tab_result, tab_input = st.tabs(["📝 결과", "✏️ 입력 수정"])
        with tab_input:
            _render_input_tab(info, auto_regions, auto_menus)
        with tab_result:
            st.caption("결과는 아래에 표시됩니다")
    else:
        _render_input_tab(info, auto_regions, auto_menus)

    # 생성 실행
    if btn_generate:
        form = st.session_state.get("_form_data", {})
        region_list = parse_comma_separated(form.get("regions", ""))
        menu_list = parse_comma_separated(form.get("menus", ""))
        if not region_list or not menu_list:
            st.error("지역과 메뉴를 최소 하나씩 입력해주세요.")
        else:
            my_review = build_my_review(
                form.get("review_vibe", ""), form.get("review_cook", ""),
                form.get("review_wait", ""), form.get("review_revisit", ""),
                st.session_state.get("review_best", ""),
                st.session_state.get("pr_complaints", ""),
                "", "",
            )

            detailed_review = _build_detailed_review_from_form()

            mood_parts = [form.get("mood", "")]
            for key, label in [("parking_info", "주차"), ("access_info", "접근성"),
                               ("restroom", "화장실"), ("facilities", "편의시설")]:
                val = form.get(key, "")
                if val and val.strip():
                    mood_parts.append(f"{label}: {val}")
            full_mood = ", ".join([p for p in mood_parts if p])

            on_generate(
                info["name"], region_list, menu_list,
                form.get("companion", ""), full_mood, form.get("memo", ""),
                form.get("ordered_menus", ""), my_review,
                None,
                detailed_review=detailed_review,
                visit_reason=form.get("visit_reason", ""),
            )
