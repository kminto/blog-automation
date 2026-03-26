"""
음식점 상세 정보 및 입력 폼 모듈
짧은 메모만 적으면 → 내 말투로 자동 확장 → 블로그 글 생성.
"""

import streamlit as st

from modules.validators import parse_comma_separated
from modules.place_search import extract_region_from_address, extract_menus_from_category
from modules.photo_analyzer import (
    analyze_photos,
    extract_menus_from_analysis,
    extract_descriptions_from_analysis,
)
from modules.memo_expander import expand_all_inputs
from ui.helpers import build_my_review, build_auto_memo
from ui.photo_section import render_photo_section
from utils.api_utils import safe_api_call


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
    st.subheader("✏️ 간단히 적으면 내 말투로 자동 확장돼요")
    st.caption("키워드만 적어도 OK! 🪄 버튼 누르면 3~4줄로 늘려줘요")

    ordered_menus = st.text_area(
        "🍽 주문한 메뉴 - 한줄평",
        placeholder="양꼬치 - 맛있음, 숯불향 좋음\n생맥주 - 고기랑 찰떡\n볶음밥 - 마지막에 먹으면 꿀",
        height=100,
        key="input_ordered",
    )

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        review_best = st.text_input("👍 제일 맛있었던 것", placeholder="채끝 미쳤음", key="review_best")
        review_worst = st.text_input("👎 아쉬웠던 점", placeholder="양 적음, 소스 아쉬움", key="review_worst")
    with col_r2:
        companion = st.text_input("👫 동행", placeholder="친구 2명", key="input_companion")
        review_episode = st.text_input("💬 에피소드", placeholder="옆테이블에서 뭐먹냐고 물어봄", key="review_episode")

    mood = st.text_input("✨ 분위기/내부", placeholder="깔끔, 테이블 넓음, 회식 좋음", key="input_mood")

    # 빠른 선택 (접을 수 있게)
    with st.expander("📋 빠른 선택 (선택사항)", expanded=False):
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            review_vibe = st.selectbox(
                "핵심 포인트",
                ["가성비 좋음", "고급짐/특별한 날", "양 많음", "맛은 좋은데 비쌈",
                 "동네 단골각", "데이트 맛집", "가족모임 적합", "혼밥 가능"],
                key="review_vibe",
            )
            review_cook = st.selectbox(
                "조리 방식",
                ["직원이 구워줌", "내가 직접 구움", "이미 조리돼서 나옴",
                 "셰프가 눈앞에서 조리", "셀프바/뷔페", "해당없음"],
                key="review_cook",
            )
        with col_s2:
            review_wait = st.selectbox(
                "웨이팅",
                ["웨이팅 없음", "5~10분 대기", "10~30분 대기",
                 "30분 이상 대기", "예약해서 바로 입장"],
                key="review_wait",
            )
            review_revisit = st.selectbox(
                "재방문 의사",
                ["무조건 재방문", "가끔 올만함", "한번은 갈만함",
                 "글쎄.. 다음엔 다른데", "비추"],
                key="review_revisit",
            )

    memo = st.text_area(
        "📝 추가 메모",
        value=build_auto_memo(info),
        height=80,
        key="input_memo",
    )

    # 🪄 일괄 확장 버튼
    if st.button("🪄 내 말투로 일괄 확장", use_container_width=True, key="btn_expand_all"):
        raw_inputs = {
            "ordered_menus": ordered_menus,
            "best": review_best,
            "worst": review_worst,
            "episode": review_episode,
            "mood": mood,
            "memo": memo,
        }
        # 빈 항목 제외
        filled = {k: v for k, v in raw_inputs.items() if v and v.strip()}
        if not filled:
            st.warning("최소 한 항목은 입력해주세요.")
        else:
            with st.spinner("🪄 내 말투로 확장 중... (5~10초)"):
                expanded = safe_api_call(expand_all_inputs, filled)
            if expanded["success"]:
                st.session_state["expanded_inputs"] = expanded["data"]
                st.success("확장 완료!")
                st.rerun()
            else:
                st.error(f"확장 실패: {expanded['error']}")

    # 확장 결과 표시
    if st.session_state.get("expanded_inputs"):
        exp = st.session_state["expanded_inputs"]
        with st.expander("🪄 확장 결과 미리보기 (수정 가능)", expanded=True):
            for key, value in exp.items():
                if value:
                    label_map = {
                        "ordered_menus": "🍽 메뉴 리뷰",
                        "best": "👍 맛있었던 것",
                        "worst": "👎 아쉬운 점",
                        "episode": "💬 에피소드",
                        "mood": "✨ 분위기",
                        "memo": "📝 메모",
                    }
                    label = label_map.get(key, key)
                    st.text_area(label, value=value, height=80, key=f"exp_{key}")

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
            # 확장 결과가 있으면 확장된 내용 사용
            exp = st.session_state.get("expanded_inputs", {})
            final_ordered = exp.get("ordered_menus", ordered_menus)
            final_mood = exp.get("mood", mood)
            final_memo = exp.get("memo", memo)

            my_review = build_my_review(
                review_vibe, review_cook, review_wait, review_revisit,
                exp.get("best", review_best),
                exp.get("worst", review_worst),
                exp.get("episode", review_episode),
                "",
            )

            on_generate(
                info["name"], region_list, menu_list,
                companion, final_mood, final_memo,
                final_ordered, my_review,
                uploaded if uploaded else None,
            )
