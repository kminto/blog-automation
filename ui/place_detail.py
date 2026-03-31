"""
음식점 상세 정보 및 입력 폼 모듈
입력 → 버튼 1번 → 키워드분석 + 본문생성 + 품질검증 자동 완료.
"""

import streamlit as st

from modules.validators import parse_comma_separated
from modules.place_search import extract_region_from_address, extract_menus_from_category
from ui.helpers import build_my_review, build_auto_memo
from ui.photo_section import render_photo_section


def _build_detailed_review_from_form() -> dict:
    """Streamlit 세분화 후기 폼에서 detailed_review 딕셔너리를 조립한다."""
    review = {}

    # 반찬
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

    # 서비스
    sv = {}
    if st.session_state.get("sv_staff"):
        sv["staff"] = st.session_state["sv_staff"]
    if st.session_state.get("sv_extras"):
        sv["extras"] = st.session_state["sv_extras"]
    if sv:
        review["service"] = sv

    # 가격/재방문
    if st.session_state.get("pr_eval"):
        review["price_eval"] = st.session_state["pr_eval"]
    if st.session_state.get("pr_complaints"):
        review["complaints"] = st.session_state["pr_complaints"]
    if st.session_state.get("pr_revisit"):
        review["revisit"] = st.session_state["pr_revisit"]
    if st.session_state.get("pr_recommend"):
        review["recommend_to"] = st.session_state["pr_recommend"]

    # 메뉴별 상세 후기 (주문한 메뉴 입력에서 파싱)
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
    """선택된 음식점 상세 정보를 표시하고 간소화된 입력 폼을 렌더링한다.
    on_analyze는 사용하지 않음 (호환성 유지). on_generate가 전체 파이프라인."""
    info = st.session_state.place_detail

    st.subheader(f"🏪 {info['name']}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**기본 정보**")
        st.text(f"📍 주소: {info['road_address'] or info['address']}")
        st.text(f"📂 카테고리: {info['category']}")
        st.text(f"📞 전화: {info['telephone'] or '정보 없음'}")
    with col2:
        st.markdown("**상세 정보**")
        st.text(f"🕐 영업시간: {info.get('business_hours') or '정보 없음'}")
        st.text(f"🅿️ 주차: {info.get('parking') or '정보 없음'}")
        st.text(f"📅 예약: {info.get('reservation') or '정보 없음'}")

    if info.get("menus"):
        st.markdown(f"**🍽️ 메뉴:** {', '.join(info['menus'][:10])}")

    st.divider()

    # 지역/메뉴 자동 추출
    auto_regions = extract_region_from_address(
        info.get("road_address", ""),
        jibun_address=info.get("address", ""),
    )
    auto_menus = info.get("menus", [])
    if not auto_menus:
        auto_menus = extract_menus_from_category(info.get("category", ""))

    regions = st.text_input("지역 (쉼표 구분)", value=", ".join(auto_regions), key="input_regions")
    menus = st.text_input("대표 메뉴 (쉼표 구분)", value=", ".join(auto_menus[:5]), key="input_menus")

    # ==============================================
    # 간소화된 입력 (짧게 적으면 내 말투로 자동 확장)
    # ==============================================
    # 서론 → 매장 → 본론 → 결론
    # ==============================================

    # --- 서론 ---
    st.subheader("📍 서론")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        visit_reason = st.text_input(
            "🚶 방문 계기",
            placeholder="친구 추천 / 검색해서 / 지나가다 발견",
            key="input_visit_reason",
        )
    with col_s2:
        companion = st.text_input("👫 동행", placeholder="친구 2명, 부모님", key="input_companion")

    # --- 매장 소개 ---
    st.subheader("🏪 매장 소개")
    mood = st.text_input("✨ 분위기/내부", placeholder="깔끔, 넓은 테이블, 인테리어 예쁨, 회식 좋음", key="input_mood")

    st.caption("📍 지도 삽입 → 네이버 에디터에서 '지도' 버튼으로 직접 추가하세요")

    # 블로그에서 자동 수집된 시설 정보를 기본값으로 표시
    auto_parking = " / ".join(info.get("parking_details", []))
    auto_restroom = " / ".join(info.get("restroom_info", []))
    auto_access = " / ".join(info.get("access_info", []))
    auto_facilities = " / ".join(info.get("facilities_info", []))

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        parking_info = st.text_input(
            "🅿️ 주차 (자동 수집됨, 수정 가능)",
            value=st.session_state.get("input_parking", auto_parking),
            placeholder="건물 지하 1시간 무료 / 근처 공영주차장 / 불가",
            key="input_parking",
        )
        access_info = st.text_input(
            "🚇 접근성 (자동 수집됨, 수정 가능)",
            value=st.session_state.get("input_access", auto_access),
            placeholder="판교역 도보 5분 / 버스 정류장 앞",
            key="input_access",
        )
    with col_m2:
        restroom = st.text_input(
            "🚻 화장실 (자동 수집됨, 수정 가능)",
            value=st.session_state.get("input_restroom", auto_restroom),
            placeholder="매장 내 깨끗 / 건물 공용",
            key="input_restroom",
        )
        facilities = st.text_input(
            "🪑 기타 편의시설 (자동 수집됨, 수정 가능)",
            value=st.session_state.get("input_facilities", auto_facilities),
            placeholder="유아의자, 단체석, 콘센트",
            key="input_facilities",
        )

    # --- 본론 (메뉴 후기) ---
    st.subheader("🍽 본론 - 메뉴 후기")
    ordered_menus = st.text_area(
        "주문한 메뉴 - 한줄평",
        placeholder="팟타이 - 면 쫄깃, 새우 탱글\n똠양꿍 - 국물 시원, 매콤\n볶음밥 - 마지막에 먹으면 꿀",
        height=100,
        key="input_ordered",
    )
    review_best = st.text_input("👍 제일 맛있었던 것", placeholder="팟타이 면 식감이 미쳤음", key="review_best")

    # --- 결론 ---
    st.subheader("💬 결론")
    review_worst = st.text_input("👎 아쉬운 점 (없으면 비워두세요)", placeholder="주차 불편, 양 적음", key="review_worst")

    # 빠른 선택 (체크박스 - 해당하는 것만 체크)
    with st.expander("📋 빠른 선택 (해당하는 것만 체크)", expanded=False):
        st.caption("체크 안 하면 본문에 포함되지 않아요")

        st.markdown("**핵심 포인트**")
        col_v1, col_v2 = st.columns(2)
        vibe_options = ["가성비 좋음", "고급짐/특별한 날", "양 많음", "맛은 좋은데 비쌈",
                        "동네 단골각", "데이트 맛집", "가족모임 적합", "혼밥 가능"]
        vibe_selected = []
        for i, opt in enumerate(vibe_options):
            col = col_v1 if i % 2 == 0 else col_v2
            with col:
                if st.checkbox(opt, key=f"vibe_{i}"):
                    vibe_selected.append(opt)

        st.markdown("**조리 방식**")
        cook_options = ["직원이 구워줌", "내가 직접 구움", "이미 조리돼서 나옴",
                        "셰프가 눈앞에서 조리"]
        review_cook = ""
        for opt in cook_options:
            if st.checkbox(opt, key=f"cook_{opt}"):
                review_cook = opt

        col_w1, col_w2 = st.columns(2)
        with col_w1:
            st.markdown("**웨이팅**")
            wait_options = ["웨이팅 없음", "5~10분 대기", "10~30분 대기",
                            "30분 이상 대기", "예약해서 바로 입장"]
            review_wait = ""
            for opt in wait_options:
                if st.checkbox(opt, key=f"wait_{opt}"):
                    review_wait = opt
        with col_w2:
            st.markdown("**재방문 의사**")
            revisit_options = ["무조건 재방문", "가끔 올만함", "한번은 갈만함", "비추"]
            review_revisit = ""
            for opt in revisit_options:
                if st.checkbox(opt, key=f"revisit_{opt}"):
                    review_revisit = opt

    # 빠른선택 결과 조합
    review_vibe = ", ".join(vibe_selected) if vibe_selected else ""

    memo = st.text_area(
        "📝 추가 메모",
        value=build_auto_memo(info),
        height=80,
        key="input_memo",
    )

    # ==============================================
    # 세분화 후기 입력 (서비스, 반찬, 가격 등 디테일)
    # ==============================================
    with st.expander("📋 세분화 후기 (더 정확한 글 생성)", expanded=False):
        st.caption("여기 적은 내용은 본문에 빠짐없이 반영돼요!")

        # 반찬
        st.markdown("**🥢 반찬 리뷰**")
        col_sd1, col_sd2 = st.columns(2)
        with col_sd1:
            sd_items = st.text_input(
                "반찬 종류",
                placeholder="갈치속젓, 알배추, 콩나물, 버섯볶음",
                key="sd_items",
            )
            sd_highlight = st.text_input(
                "특히 맛있었던 반찬",
                placeholder="갈치속젓이 짭짤하면서 감칠맛 최고",
                key="sd_highlight",
            )
        with col_sd2:
            sd_taste = st.text_input(
                "반찬 전체 평가",
                placeholder="하나하나 다 맛있고 정성스러움",
                key="sd_taste",
            )
            sd_refill = st.text_input(
                "리필 여부",
                placeholder="갈치속젓 리필 가능",
                key="sd_refill",
            )

        st.markdown("**🍳 서비스 / 직원**")
        col_sv1, col_sv2 = st.columns(2)
        with col_sv1:
            sv_staff = st.text_input(
                "사장님/직원 평가",
                placeholder="사장님과 직원 모두 매우 친절",
                key="sv_staff",
            )
        with col_sv2:
            sv_extras = st.text_input(
                "서비스/특이사항",
                placeholder="사장님이 직접 잘라줌, 리필 해줌",
                key="sv_extras",
            )

        st.markdown("**💰 가격 / 재방문**")
        col_pr1, col_pr2 = st.columns(2)
        with col_pr1:
            pr_eval = st.text_input(
                "가격 평가",
                placeholder="1인 45,000원. 비싸지만 산낙지 품질 생각하면 납득",
                key="pr_eval",
            )
            pr_complaints = st.text_input(
                "아쉬운 점",
                placeholder="가격이 좀 있는 편",
                key="pr_complaints",
            )
        with col_pr2:
            pr_revisit = st.text_input(
                "재방문 의사",
                placeholder="재방문 100%, 다음엔 산낙지회 먹어볼 예정",
                key="pr_revisit",
            )
            pr_recommend = st.text_input(
                "추천 대상",
                placeholder="부모님, 가족 외식, 소규모 회식",
                key="pr_recommend",
            )

    st.divider()

    # 사진 업로드 (선택)
    st.markdown("**📸 사진 업로드 (선택)**")
    st.caption("사진 있으면 AI가 자동 분석해서 본문에 반영해요. 없어도 OK!")
    uploaded = st.file_uploader(
        "사진 선택 (여러 장 가능)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="photo_upload",
    )
    if uploaded:
        st.caption(f"📸 {len(uploaded)}장 선택됨 → 생성 시 자동 분석됩니다")

    with st.expander("📸 촬영 가이드 (참고용)", expanded=False):
        render_photo_section()

    st.divider()

    # 🚀 원클릭 생성 버튼
    btn_generate = st.button(
        "🚀 키워드 분석 + 본문 생성",
        use_container_width=True,
        type="primary",
        key="btn_full_pipeline",
    )

    if btn_generate:
        region_list = parse_comma_separated(regions)
        menu_list = parse_comma_separated(menus)
        if not region_list or not menu_list:
            st.error("지역과 메뉴를 최소 하나씩 입력해주세요.")
        else:
            my_review = build_my_review(
                review_vibe, review_cook, review_wait, review_revisit,
                review_best, review_worst, "",  "",
            )

            # 세분화 후기 조립
            detailed_review = _build_detailed_review_from_form()

            # 매장 정보를 mood에 합치기
            mood_parts = [mood] if mood and mood.strip() else []
            if parking_info and parking_info.strip():
                mood_parts.append(f"주차: {parking_info}")
            if access_info and access_info.strip():
                mood_parts.append(f"접근성: {access_info}")
            if restroom and restroom.strip():
                mood_parts.append(f"화장실: {restroom}")
            if facilities and facilities.strip():
                mood_parts.append(f"편의시설: {facilities}")
            full_mood = ", ".join(mood_parts)

            on_generate(
                info["name"], region_list, menu_list,
                companion, full_mood, memo,
                ordered_menus, my_review,
                uploaded if uploaded else None,
                detailed_review=detailed_review,
                visit_reason=visit_reason,
            )
