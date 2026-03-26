"""
음식점 상세 정보 및 입력 폼 모듈
선택된 음식점의 정보를 표시하고 후기/메뉴 입력 폼을 렌더링한다.
"""

import streamlit as st

from modules.validators import parse_comma_separated
from modules.place_search import extract_region_from_address, extract_menus_from_category
from modules.photo_analyzer import (
    analyze_photos,
    extract_menus_from_analysis,
    extract_descriptions_from_analysis,
)
from ui.helpers import build_my_review, build_auto_memo
from ui.photo_section import render_photo_section
from utils.api_utils import safe_api_call


def render_place_detail(on_analyze, on_generate):
    """선택된 음식점 상세 정보를 표시하고 입력 폼을 렌더링한다.

    Args:
        on_analyze: 키워드 분석 콜백 (region_list, menu_list)
        on_generate: 본문 생성 콜백 (name, regions, menus, companion, mood, memo, ordered, review)
    """
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
    st.subheader("✏️ 정보 수정 및 추가")

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
    ordered_menus = st.text_area(
        "🍽 내가 주문한 메뉴 (줄바꿈, 메뉴명 - 내 한줄평)",
        placeholder="예:\nA코스 - 육사시미가 입에서 녹았음, 막창은 좀 질겼음\n생맥주 - 고기랑 찰떡, 2잔 마심",
        height=120,
        key="input_ordered",
    )

    # 분류형 후기 입력
    st.markdown("**📝 내 솔직 후기**")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
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
    with col_r2:
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

    review_best = st.text_input(
        "제일 맛있었던 메뉴",
        placeholder="예: 채끝이 미쳤음, 육사시미 녹았음",
        key="review_best",
    )
    review_worst = st.text_input(
        "아쉬웠던 점 (솔직하게)",
        placeholder="예: 특양 질김, 소스 아쉬움, 양 적음",
        key="review_worst",
    )
    review_episode = st.text_input(
        "기억나는 에피소드 (선택)",
        placeholder="예: 옆테이블에서 뭐먹냐고 물어봄 ㅋㅋ",
        key="review_episode",
    )
    review_free = st.text_area(
        "추가로 하고싶은 말 (자유)",
        placeholder="예: 솥밥 하나 더 시킬뻔 ㅋㅋ",
        height=80,
        key="review_free",
    )

    my_review = build_my_review(
        review_vibe, review_cook, review_wait, review_revisit,
        review_best, review_worst, review_episode, review_free,
    )

    companion = st.text_input("방문 인원/동행", placeholder="예: 친구 2명")
    mood = st.text_input("분위기", placeholder="예: 조용함, 가족 분위기")
    memo = st.text_area("추가 메모 (선택)", value=build_auto_memo(info), key="input_memo")

    st.divider()

    # 사진 업로드 + AI 분석
    with st.expander("📸 사진 업로드 (AI가 자동 분석)", expanded=True):
        st.caption("촬영 순서대로 올려주세요: 외관 → 내부 → 메뉴판 → 반찬 → 메인 → 사이드")
        uploaded = st.file_uploader(
            "사진 선택 (여러 장 가능)",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="photo_upload",
        )

        if uploaded and st.button("🔍 사진 AI 분석", use_container_width=True, key="btn_photo_analyze"):
            photo_data = [{"name": f.name, "bytes": f.read()} for f in uploaded]
            with st.spinner(f"{len(photo_data)}장 분석 중... (10~20초)"):
                result = safe_api_call(analyze_photos, photo_data)
            if result["success"]:
                st.session_state["photo_analysis"] = result["data"]
                st.success(f"{len(result['data'])}장 분석 완료!")
                st.rerun()
            else:
                st.error(f"사진 분석 실패: {result['error']}")

        # 분석 결과 표시
        if st.session_state.get("photo_analysis"):
            analysis = st.session_state["photo_analysis"]
            category_icons = {
                "외관": "🏪", "내부": "🪑", "메뉴판": "📋",
                "세팅": "🥢", "메인음식": "🍽", "사이드": "🍺", "기타": "📷",
            }
            for item in analysis:
                cat = item.get("category", "기타")
                icon = category_icons.get(cat, "📷")
                food = f" **{item['food_name']}**" if item.get("food_name") else ""
                st.markdown(f"{icon} `{cat}`{food} — {item.get('description', '')}")

            # 자동 채우기 버튼
            if st.button("✨ 분석 결과로 자동 채우기", key="btn_auto_fill"):
                detected_menus = extract_menus_from_analysis(analysis)
                detected_desc = extract_descriptions_from_analysis(analysis)
                if detected_menus:
                    st.session_state["input_ordered"] = detected_desc
                    st.session_state["input_menus"] = ", ".join(detected_menus)
                st.rerun()

    # 촬영 가이드
    with st.expander("📸 촬영 가이드 (참고용)", expanded=False):
        render_photo_section()

    st.divider()

    # 액션 버튼
    col1, col2 = st.columns(2)
    with col1:
        btn_analyze = st.button("🔍 키워드 분석", use_container_width=True)
    with col2:
        btn_generate = st.button("✍️ 본문 생성", use_container_width=True)

    if btn_analyze:
        region_list = parse_comma_separated(regions)
        menu_list = parse_comma_separated(menus)
        if not region_list or not menu_list:
            st.error("지역과 메뉴를 최소 하나씩 입력해주세요.")
        else:
            on_analyze(region_list, menu_list)

    if btn_generate:
        if not st.session_state.scored_keywords:
            st.warning("먼저 키워드 분석을 실행해주세요.")
        else:
            region_list = parse_comma_separated(regions)
            menu_list = parse_comma_separated(menus)
            on_generate(
                info["name"], region_list, menu_list,
                companion, mood, memo, ordered_menus, my_review,
            )
