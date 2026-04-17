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

    # 새 항목들
    new_fields = {
        "input_reservation": "reservation",
        "input_visit_time": "visit_time",
        "input_party_size": "party_size",
        "input_waiting": "waiting",
        "input_food_wait": "food_wait_time",
        "input_total_price": "total_price",
        "input_tip": "tip",
        "input_next_menu": "next_menu",
    }
    for session_key, review_key in new_fields.items():
        val = st.session_state.get(session_key, "")
        if val and val.strip():
            review[review_key] = val

    # 내돈내산
    if st.session_state.get("input_own_money"):
        review["own_money"] = True

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
    col_name, col_save, col_refresh = st.columns([5, 1, 1])
    with col_name:
        st.subheader(f"🏪 {info['name']}")
    with col_save:
        if st.button("💾", key="btn_save_draft", help="중간 저장"):
            from modules.db import is_db_available, save_draft
            if is_db_available():
                draft_id = st.session_state.get("current_draft_id") or ""
                saved_id = save_draft(draft_id, st.session_state)
                if saved_id:
                    st.session_state["current_draft_id"] = saved_id
                    st.toast("💾 저장 완료!")
                else:
                    st.error("저장 실패 — DB 연결을 확인해주세요")
                st.rerun()
            else:
                st.error("DB 연결 불가 — Supabase 설정을 확인해주세요")
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
        col_s3, col_s4 = st.columns(2)
        with col_s3:
            st.text_input(
                "예약 방법",
                placeholder="네이버/캐치테이블/전화/현장",
                key="input_reservation",
            )
        with col_s4:
            st.text_input(
                "방문 시간대",
                placeholder="점심/저녁/브런치/야식",
                key="input_visit_time",
            )
        col_s5, col_s6 = st.columns(2)
        with col_s5:
            st.text_input(
                "방문 인원",
                placeholder="2명, 4명",
                key="input_party_size",
            )
        with col_s6:
            st.text_input(
                "웨이팅",
                placeholder="없음/10분/30분+",
                key="input_waiting",
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
            placeholder="팟타이 12,000원 - 면 쫄깃\n똠양꿍 15,000원 - 국물 시원",
            height=80,
            key="input_ordered",
        )
        st.text_input(
            "사이드 · 추천 메뉴 (선택)",
            placeholder="볶음밥, 디저트",
            key="input_side_menu",
        )
        st.text_area(
            "맛 평가",
            placeholder="전체적으로 간이 딱, 소스 특이\n고기 육즙 좋음, 밑반찬 정성스러움",
            height=100,
            key="sd_taste",
        )
        st.text_input(
            "음식 나오는 시간",
            placeholder="주문 후 10분",
            key="input_food_wait",
        )

        # ── ⭐ 총평 ──
        st.markdown("**⭐ 총평**")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.text_input(
                "총 결제금액",
                placeholder="2인 58,000원",
                key="input_total_price",
            )
        with col_t2:
            st.text_input(
                "서비스",
                placeholder="친절, 직접 잘라줌",
                key="sv_staff",
            )
        col_t3, col_t4 = st.columns(2)
        with col_t3:
            st.text_input(
                "재방문 의사",
                placeholder="100% 재방문",
                key="pr_revisit",
            )
        with col_t4:
            st.text_input(
                "추천 대상 · 이유",
                placeholder="데이트, 가족 모임",
                key="pr_recommend",
            )
        st.text_input(
            "추천 조합 · 꿀팁",
            placeholder="삼겹살+된장찌개 세트 강추, 소주보다 하이볼",
            key="input_tip",
        )
        st.text_input(
            "다음에 먹어볼 메뉴",
            placeholder="냉면, 갈비탕",
            key="input_next_menu",
        )
        st.text_input(
            "아쉬운 점 (선택)",
            placeholder="웨이팅 길어요, 양 적음",
            key="pr_complaints",
        )
        st.checkbox("내돈내산", key="input_own_money", value=True)

    # === 1단계: 키워드 분석 ===
    has_keywords = st.session_state.get("scored_keywords") is not None

    if not has_keywords:
        btn_keyword = st.button(
            "🔍 1단계: 키워드 분석",
            use_container_width=True,
            type="primary",
            key="btn_keyword_analysis",
        )
        if btn_keyword:
            region_list = parse_comma_separated(st.session_state.get("input_regions", ""))
            menu_list = parse_comma_separated(st.session_state.get("input_menus", ""))
            if not region_list or not menu_list:
                st.error("지역과 메뉴를 최소 하나씩 입력해주세요.")
            else:
                from modules.pipeline import run_keyword_only
                user_context = " ".join([
                    st.session_state.get("input_companion", ""),
                    st.session_state.get("input_mood", ""),
                    st.session_state.get("input_ordered", ""),
                    st.session_state.get("input_visit_reason", ""),
                ])
                run_keyword_only(region_list, menu_list, user_context)
                st.rerun()

    # === 키워드 선택 ===
    if has_keywords:
        st.subheader("📊 키워드 선택")
        st.caption("상위 노출에 사용할 키워드를 선택하세요 (3개 추천)")

        keywords = st.session_state.scored_keywords
        # 기본 선택: 상위 3개
        if "selected_keywords" not in st.session_state:
            st.session_state["selected_keywords"] = [
                kw["keyword"] for kw in keywords[:3]
            ]

        selected = []
        for i, kw in enumerate(keywords):
            cols = st.columns([0.5, 3, 1.5, 1, 1])
            with cols[0]:
                checked = st.checkbox(
                    "", value=(kw["keyword"] in st.session_state["selected_keywords"]),
                    key=f"kw_check_{i}", label_visibility="collapsed",
                )
            with cols[1]:
                st.text(kw["keyword"])
            with cols[2]:
                st.text(f"검색량 {kw.get('search_volume', 0):,}")
            with cols[3]:
                st.text(kw.get("competition", ""))
            with cols[4]:
                st.text(f"{kw.get('score', 0):,.0f}점")
            if checked:
                selected.append(kw)

        st.session_state["selected_keywords"] = [kw["keyword"] for kw in selected]

        if not selected:
            st.warning("최소 1개 키워드를 선택해주세요.")

        # 키워드 재분석 버튼
        col_re, col_gen = st.columns(2)
        with col_re:
            if st.button("🔄 키워드 재분석", use_container_width=True, key="btn_re_keyword"):
                st.session_state["scored_keywords"] = None
                st.session_state.pop("selected_keywords", None)
                st.rerun()
        with col_gen:
            btn_generate = st.button(
                "✍️ 2단계: 본문 생성",
                use_container_width=True,
                type="primary",
                key="btn_generate_blog",
                disabled=len(selected) == 0,
            )

        # === 2단계: 본문 생성 ===
        if btn_generate and selected:
            # 선택된 키워드만 세션에 저장
            st.session_state.scored_keywords = selected

            region_list = parse_comma_separated(st.session_state.get("input_regions", ""))
            menu_list = parse_comma_separated(st.session_state.get("input_menus", ""))
            detailed_review = _build_detailed_review_from_form()

            memo = build_auto_memo(info)
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

            ordered = st.session_state.get("input_ordered", "")
            side = st.session_state.get("input_side_menu", "")
            if side and side.strip():
                ordered += f"\n{side.strip()} - 사이드"

            from modules.pipeline import run_blog_only
            run_blog_only(
                info["name"], region_list, menu_list,
                st.session_state.get("input_companion", ""),
                full_mood, memo, ordered,
                place_detail=info,
                detailed_review=detailed_review,
                visit_reason=st.session_state.get("input_visit_reason", ""),
            )
