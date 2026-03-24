"""
맛집 블로그 자동화 시스템 - 메인 Streamlit 앱
"""

import streamlit as st
import pandas as pd

from modules.validators import validate_env, parse_comma_separated
from modules.place_search import (
    search_restaurant,
    extract_region_from_address,
    extract_menus_from_category,
)
from modules.place_detail import fetch_place_detail, merge_place_info
from modules.keyword_extractor import generate_keyword_combinations, filter_meaningful_keywords
from modules.naver_api import fetch_keyword_stats_batch
from modules.datalab_api import fetch_search_trend, analyze_trend
from modules.keyword_scorer import score_keyword, rank_keywords
from modules.blog_writer import generate_blog_post
from modules.hashtag_generator import generate_hashtags
from modules.html_converter import blog_text_to_html
from modules.photo_manager import get_shot_guide
from modules.blog_analytics import fetch_blog_stats, analyze_blog_growth
from modules.blog_advisor import (
    get_trending_topics,
    get_posting_stats,
    get_publish_checklist,
    generate_weekly_plan,
    add_posting_record,
    get_neighbor_recommendations,
    generate_comment_templates,
    get_daily_routine,
    save_topic_plan,
    get_today_topic,
    get_upcoming_topics,
)
from utils.api_utils import safe_api_call

# === 페이지 설정 ===
st.set_page_config(
    page_title="맛집 블로그 자동화",
    page_icon="🍽️",
    layout="wide",
)

# === 비밀번호 잠금 ===
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("#### 🔒 로그인")
    pw = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if pw == st.secrets.get("APP_PASSWORD", ""):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

st.markdown("#### 개인 테스트 프로그램 만들기")

# 오늘 예정된 주제 알림
_today_topic = get_today_topic()
if _today_topic and not _today_topic.get("done"):
    st.markdown(
        f'<div style="background:#fff3cd;border-left:4px solid #ff9800;'
        f'padding:12px 16px;border-radius:4px;margin-bottom:12px;">'
        f'📌 <b>오늘의 주제:</b> {_today_topic["topic"]}'
        f'<br><span style="color:#888;font-size:12px;">'
        f'어제 정한 주제예요. 아래에서 검색해서 바로 시작하세요!</span></div>',
        unsafe_allow_html=True,
    )


def init_session_state():
    """세션 상태를 초기화한다."""
    defaults = {
        "keyword_results": None,
        "scored_keywords": None,
        "blog_result": None,
        "hashtags": None,
        "search_results": None,
        "selected_place": None,
        "place_detail": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()

# === 환경변수 검증 ===
missing_keys = validate_env()
if missing_keys:
    st.error(f"환경변수가 설정되지 않았습니다: {', '.join(missing_keys)}")
    st.info("`.env` 파일을 확인해주세요. `.env.example`을 참고하세요.")
    st.stop()


# ============================================================
# 헬퍼 함수 정의 (호출보다 위에 위치해야 함)
# ============================================================

def _set_clipboard(key: str, text: str):
    """클립보드 복사용 세션 상태를 설정한다."""
    st.session_state[f"copied_{key}"] = text


def _parse_blog_sections(text: str) -> dict:
    """생성된 블로그 텍스트에서 제목/본문/해시태그를 분리한다."""
    sections = {"titles": "", "body": "", "hashtags": ""}
    if "### 본문" in text:
        parts = text.split("### 본문")
        sections["titles"] = parts[0].replace("### 제목 후보", "").strip()
        body_part = parts[1]
        if "### 해시태그" in body_part:
            body_parts = body_part.split("### 해시태그")
            sections["body"] = body_parts[0].strip()
            sections["hashtags"] = body_parts[1].strip()
        else:
            sections["body"] = body_part.strip()
    else:
        sections["body"] = text
    return sections


def _run_routine_panel(routine_key: str):
    """각 루틴의 실행 패널을 표시한다."""

    if routine_key == "trend":
        # 트렌드 키워드 확인
        st.markdown("---")
        with st.spinner("트렌드 분석 중..."):
            topics = get_trending_topics()
        st.markdown("**오늘의 트렌드 키워드:**")
        for t in topics[:7]:
            trend_icon = "📈" if t["trend"] == "상승" else "📉" if t["trend"] == "하락" else "➡️"
            st.markdown(f"{trend_icon} **{t['keyword']}** ({t['type']}) - {t['priority']}")
        if st.button("✅ 확인 완료", key="done_trend"):
            st.session_state["routine_done"]["trend"] = True
            st.session_state["routine_open_trend"] = False
            st.rerun()

    elif routine_key == "write":
        # 글쓰기 → 메인 화면에서 진행
        st.markdown("---")
        st.info("왼쪽에서 음식점 검색 → 키워드 분석 → 본문 생성 후 완료 체크하세요")
        if st.button("✅ 글 발행 완료", key="done_write"):
            st.session_state["routine_done"]["write"] = True
            st.session_state["routine_open_write"] = False
            st.rerun()

    elif routine_key == "visit":
        # 이웃 방문
        st.markdown("---")
        with st.spinner("추천 블로그 검색 중..."):
            blogs = get_neighbor_recommendations()
        st.markdown("**아래 3곳 방문 → 공감 + 댓글:**")
        for i, b in enumerate(blogs[:3], 1):
            st.markdown(f"{i}. [{b['blogger']}]({b['link']})")
            st.caption(f"   {b['title'][:40]}")

        st.markdown("**댓글 템플릿 (복사해서 사용):**")
        templates = generate_comment_templates()
        for t in templates[:2]:
            st.code(t["text"], language=None)

        if st.button("✅ 3곳 방문 완료", key="done_visit"):
            st.session_state["routine_done"]["visit"] = True
            st.session_state["routine_open_visit"] = False
            st.rerun()

    elif routine_key == "reply":
        # 댓글 답글
        st.markdown("---")
        st.markdown(
            '[내 블로그 댓글 확인하기](https://blog.naver.com/rinx_x)'
        )
        st.caption("새 댓글이 있으면 답글 달기 → 활동 지표 UP")
        if st.button("✅ 답글 완료", key="done_reply"):
            st.session_state["routine_done"]["reply"] = True
            st.session_state["routine_open_reply"] = False
            st.rerun()

    elif routine_key == "plan":
        # 내일 주제 정하기
        st.markdown("---")
        plan = generate_weekly_plan()
        tomorrow = plan[1] if len(plan) > 1 else plan[0]
        st.markdown(f"**내일 추천 주제:** {tomorrow['theme']}")
        st.caption(f"발행 시간: {tomorrow['publish_time']} | 힌트: {tomorrow['keyword_hint']}")

        # 예정된 주제 표시
        upcoming = get_upcoming_topics()
        if upcoming:
            st.markdown("**예정된 주제:**")
            for u in upcoming[:5]:
                icon = "✅" if u.get("done") else "📝"
                st.caption(f"{icon} {u['date']} - {u['topic']}")

        tomorrow_topic = st.text_input(
            "내일 쓸 주제 (음식점 이름 or 키워드)",
            placeholder="예: 모란역 돼지국밥",
            key="tomorrow_topic",
        )
        if st.button("✅ 주제 저장 완료", key="done_plan"):
            if tomorrow_topic and tomorrow_topic.strip():
                save_topic_plan(tomorrow_topic.strip())
                st.session_state["routine_done"]["plan"] = True
                st.session_state["routine_open_plan"] = False
                st.rerun()
            else:
                st.warning("주제를 입력해주세요.")


def _render_advisor_dashboard():
    """블로그 성장 대시보드를 렌더링한다."""

    # 내 블로그 분석
    if st.button("📊 내 블로그 분석", key="btn_my_blog"):
        st.session_state["show_analytics"] = True

    if st.session_state.get("show_analytics"):
        with st.spinner("블로그 데이터 수집 중..."):
            raw = fetch_blog_stats("rinx_x")
            analysis = analyze_blog_growth(raw)

        # 핵심 지표
        col1, col2, col3 = st.columns(3)
        col1.metric("총 포스팅", f"{analysis['total']}개")
        col2.metric("맛집 비율", f"{analysis['food_ratio']}%")
        col3.metric("월평균", f"{analysis['avg_per_month']}개")

        # 최근/첫 글
        if analysis.get("latest_post"):
            st.caption(f"최근 글: {analysis['latest_post']['date']} | {analysis['latest_post']['title'][:30]}")
        if analysis.get("first_post"):
            st.caption(f"첫 글: {analysis['first_post']['date']}")

        # 월별 추이 차트
        monthly = analysis.get("monthly", {})
        if monthly:
            st.markdown("**월별 포스팅 추이**")
            chart_data = {k: v for k, v in monthly.items()}
            st.bar_chart(chart_data)

        # 성장 진단
        st.markdown("**성장 진단**")
        for tip in analysis.get("diagnosis", []):
            st.markdown(f"{tip['icon']} **{tip['title']}** - {tip['detail']}")
            st.caption(f"→ {tip['action']}")

    st.markdown("---")

    # 일일 루틴 (실행형)
    if "routine_done" not in st.session_state:
        st.session_state["routine_done"] = {}

    routines = [
        {"key": "trend", "label": "🔍 트렌드 키워드 확인", "min": 2},
        {"key": "write", "label": "✍️ 블로그 글 작성 + 발행", "min": 5},
        {"key": "visit", "label": "💬 이웃 블로그 3곳 방문", "min": 5},
        {"key": "reply", "label": "💌 내 글 댓글 답글", "min": 3},
        {"key": "plan", "label": "📅 내일 주제 정하기", "min": 2},
    ]

    done_count = sum(1 for r in routines if st.session_state["routine_done"].get(r["key"]))
    st.markdown(f"**오늘의 루틴** ({done_count}/{len(routines)} 완료)")

    for r in routines:
        is_done = st.session_state["routine_done"].get(r["key"], False)
        if is_done:
            st.markdown(f"✅ ~~{r['label']}~~ ({r['min']}분)")
        else:
            if st.button(f"▶ {r['label']} ({r['min']}분)", key=f"routine_{r['key']}"):
                st.session_state[f"routine_open_{r['key']}"] = True

            # 각 루틴 실행 패널
            if st.session_state.get(f"routine_open_{r['key']}"):
                _run_routine_panel(r["key"])

    if done_count == len(routines):
        st.success("오늘 루틴 올클리어! 🎉")

    st.markdown("---")

    # 소통 도우미
    if st.button("💬 이웃 소통 도우미", key="btn_neighbor"):
        st.session_state["show_neighbor"] = True

    if st.session_state.get("show_neighbor"):
        st.markdown("**방문 추천 블로그:**")
        blogs = get_neighbor_recommendations()
        for b in blogs:
            st.markdown(f"[{b['blogger']}]({b['link']})\n{b['title'][:30]}...")

        st.markdown("**댓글 템플릿:**")
        templates = generate_comment_templates()
        for t in templates:
            st.code(t["text"], language=None)

    # 주간 플랜 / 트렌드
    if st.button("📅 주간 플랜", key="btn_weekly"):
        for day in generate_weekly_plan():
            st.markdown(f"**{day['date']}** {day['theme']} | {day['publish_time']}")

    if st.button("🔥 트렌드 추천", key="btn_trend"):
        for t in get_trending_topics()[:5]:
            icon = "📈" if t["trend"] == "상승" else "➡️"
            st.markdown(f"{icon} {t['keyword']} ({t['type']})")


def _render_blog_result():
    """블로그 생성 결과를 섹션별로 표시한다."""
    text = st.session_state.blog_result
    sections = _parse_blog_sections(text)

    st.markdown(
        '<a href="https://blog.naver.com/GoBlogWrite.naver" target="_blank">'
        '<button style="background:#03c75a;color:white;border:none;'
        'padding:12px 24px;border-radius:8px;font-size:16px;'
        'cursor:pointer;width:100%;margin-bottom:16px;">'
        '✏️ 네이버 블로그 글쓰기 열기</button></a>',
        unsafe_allow_html=True,
    )

    if sections["titles"]:
        st.subheader("📌 제목 후보")
        st.text_area("제목 (원하는 걸 골라서 복사)", value=sections["titles"], height=120, key="ta_titles")

    st.subheader("📝 본문")
    tab_text, tab_html = st.tabs(["텍스트 (일반 복사)", "HTML (서식 복사)"])
    with tab_text:
        st.text_area("본문 텍스트", value=sections["body"], height=400, key="ta_body")
    with tab_html:
        body_html = blog_text_to_html(sections["body"])
        st.markdown(
            '<p style="color:#666;font-size:13px;">'
            '📋 복사 → 네이버 에디터에 붙여넣기 → 📷 자리에 촬영 가이드 순서대로 사진 넣기</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="border:1px solid #ddd;padding:20px;border-radius:8px;'
            f'max-height:500px;overflow-y:auto;background:white;">'
            f'{body_html}</div>',
            unsafe_allow_html=True,
        )

    if sections["hashtags"]:
        st.subheader("🏷 해시태그 (본문 내)")
        st.code(sections["hashtags"], language=None)


def _build_auto_memo(info: dict) -> str:
    """수집된 정보로 자동 메모를 구성한다."""
    parts = []
    if info.get("business_hours"):
        parts.append(f"영업시간: {info['business_hours']}")
    if info.get("parking"):
        parts.append(f"주차: {info['parking']}")
    if info.get("reservation"):
        parts.append(f"예약: {info['reservation']}")
    if info.get("telephone"):
        parts.append(f"전화: {info['telephone']}")
    if info.get("facilities"):
        parts.append(f"편의시설: {', '.join(info['facilities'][:5])}")
    return "\n".join(parts)


def _render_photo_section():
    """촬영 가이드를 가독성 좋은 카드 형태로 렌더링한다."""
    guide = get_shot_guide()

    st.markdown(
        '<div style="background:#f0f8f0;border-radius:8px;padding:12px 16px;margin-bottom:12px;">'
        '<b>📸 사용법 3단계</b><br>'
        '① 아래 순서대로 사진 찍기<br>'
        '② 앱에서 본문 생성 → 텍스트 복사<br>'
        '③ 네이버 에디터에 붙여넣기 → 📷 자리에 사진 넣기</div>',
        unsafe_allow_html=True,
    )

    # 촬영 가이드를 카테고리별로 묶어서 표시
    categories = {
        "🏪 매장": [s for s in guide if s["slot"] <= 2],
        "🪑 내부": [s for s in guide if 3 <= s["slot"] <= 4],
        "📋 메뉴판": [s for s in guide if s["slot"] == 5],
        "🥢 기본세팅": [s for s in guide if s["slot"] == 6],
        "🍖 메인1": [s for s in guide if 7 <= s["slot"] <= 9],
        "🍖 메인2": [s for s in guide if 10 <= s["slot"] <= 11],
        "🍺 사이드": [s for s in guide if s["slot"] == 12],
        "📸 추가": [s for s in guide if s["slot"] == 13],
    }

    for cat_name, shots in categories.items():
        if not shots:
            continue
        items = " → ".join([f"**{s['label']}**" for s in shots])
        tips = " / ".join([s["tip"] for s in shots])
        st.markdown(f"{cat_name} {items}")
        st.caption(f"💡 {tips}")

    st.markdown("---")
    st.markdown(
        "**본문에서 이렇게 표시됩니다:**\n\n"
        "`📷 1번 사진 - 가게 간판이 보이게 정면에서 한 장`\n\n"
        "→ 네이버 에디터에서 이 자리에 1번 사진을 넣으면 끝!"
    )


def _render_place_detail():
    """선택된 음식점 상세 정보를 표시하고 입력 폼을 렌더링한다."""
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
        "🍽 내가 주문한 메뉴 (줄바꿈으로 구분, 메뉴명 + 한줄 설명)",
        placeholder="예:\nA코스 - 육사시미+고기4종+꼬리구이+솥밥\n생맥주 - 시원하게 한잔\n마파두부 - 사이드로 시킴",
        height=120,
        key="input_ordered",
    )
    companion = st.text_input("방문 인원/동행", placeholder="예: 친구 2명")
    mood = st.text_input("분위기", placeholder="예: 조용함, 가족 분위기")
    memo = st.text_area("추가 메모 (선택)", value=_build_auto_memo(info), key="input_memo")

    st.divider()

    # 사진 관리
    with st.expander("📸 사진 관리 (촬영 가이드 + 업로드)", expanded=False):
        _render_photo_section()

    st.divider()

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
            _run_keyword_analysis(region_list, menu_list)

    if btn_generate:
        if not st.session_state.scored_keywords:
            st.warning("먼저 키워드 분석을 실행해주세요.")
        else:
            region_list = parse_comma_separated(regions)
            menu_list = parse_comma_separated(menus)
            _run_blog_generation(
                info["name"], region_list, menu_list,
                companion, mood, memo, ordered_menus,
            )


def _run_keyword_analysis(region_list: list[str], menu_list: list[str]):
    """키워드 분석을 실행한다."""
    with st.spinner("키워드 조합 생성 중..."):
        combinations = generate_keyword_combinations(region_list, menu_list)
        combinations = filter_meaningful_keywords(combinations)
        st.info(f"총 {len(combinations)}개 키워드 조합 생성 완료")

    with st.spinner("네이버 키워드도구 API 조회 중..."):
        api_result = safe_api_call(fetch_keyword_stats_batch, combinations)
        if not api_result["success"]:
            st.error(f"키워드 API 오류: {api_result['error']}")
            return
        keyword_stats = api_result["data"]

    with st.spinner("검색 트렌드 분석 중..."):
        top_for_trend = sorted(
            keyword_stats,
            key=lambda x: (
                (x.get("monthlyPcQcCnt", 0) if isinstance(x.get("monthlyPcQcCnt", 0), int) else 5)
                + (x.get("monthlyMobileQcCnt", 0) if isinstance(x.get("monthlyMobileQcCnt", 0), int) else 5)
            ),
            reverse=True,
        )[:5]
        trend_keywords = [kw.get("relKeyword", "") for kw in top_for_trend]
        trend_result = safe_api_call(fetch_search_trend, trend_keywords)
        trend_map = {}
        if trend_result["success"] and trend_result["data"]:
            for r in trend_result["data"].get("results", []):
                trend_map[r.get("title", "")] = analyze_trend(r.get("data", []))

    with st.spinner("키워드 점수 계산 중..."):
        scored = []
        for kw_data in keyword_stats:
            keyword = kw_data.get("relKeyword", "")
            trend = trend_map.get(keyword, "유지")
            scored.append(score_keyword(kw_data, trend))
        ranked = rank_keywords(scored, regions=region_list, menus=menu_list)
        st.session_state.scored_keywords = ranked

    st.success("키워드 분석 완료!")


def _run_blog_generation(
    restaurant_name: str,
    region_list: list[str],
    menu_list: list[str],
    companion: str,
    mood: str,
    memo: str,
    ordered_menus: str = "",
):
    """블로그 본문을 생성한다."""
    full_memo = memo
    if ordered_menus and ordered_menus.strip():
        full_memo += "\n\n[내가 주문한 메뉴]\n" + ordered_menus.strip()

    with st.spinner("ChatGPT가 블로그 글을 작성하고 있습니다..."):
        result = safe_api_call(
            generate_blog_post,
            restaurant_name=restaurant_name,
            regions=region_list,
            menus=menu_list,
            companion=companion,
            mood=mood,
            memo=full_memo,
            top_keywords=st.session_state.scored_keywords,
        )
        if not result["success"]:
            st.error(f"본문 생성 오류: {result['error']}")
            return
        st.session_state.blog_result = result["data"]

    with st.spinner("해시태그 생성 중..."):
        hashtag_list = generate_hashtags(
            restaurant_name=restaurant_name,
            regions=region_list,
            menus=menu_list,
            top_keywords=st.session_state.scored_keywords,
            mood=mood,
        )
        st.session_state.hashtags = hashtag_list

    top_kws = [kw["keyword"] for kw in (st.session_state.scored_keywords or [])[:3]]
    add_posting_record(
        restaurant=restaurant_name,
        region=", ".join(region_list),
        keywords=top_kws,
        title=restaurant_name,
    )
    st.success("블로그 글 생성 완료!")


# ============================================================
# 메인 실행 코드
# ============================================================

# === 사이드바: 음식점 검색 ===
with st.sidebar:
    st.header("🔍 음식점 검색")
    search_query = st.text_input("음식점 이름", placeholder="예: 모란돼지국밥")

    col_search, col_reset = st.columns(2)
    with col_search:
        btn_search = st.button("🔍 검색", use_container_width=True)
    with col_reset:
        btn_reset = st.button("🔄 초기화", use_container_width=True)

# === 초기화 ===
if btn_reset:
    for key in [
        "keyword_results", "scored_keywords", "blog_result",
        "hashtags", "search_results", "selected_place", "place_detail",
    ]:
        st.session_state[key] = None
    st.rerun()

# === 음식점 검색 ===
if btn_search and search_query:
    with st.spinner("음식점 검색 중..."):
        result = safe_api_call(search_restaurant, search_query)
        if result["success"] and result["data"]:
            st.session_state.search_results = result["data"]
            st.session_state.selected_place = None
            st.session_state.place_detail = None
        else:
            st.error(f"검색 실패: {result.get('error', '결과가 없습니다.')}")

# === 검색 결과 표시 및 선택 ===
if st.session_state.search_results and not st.session_state.selected_place:
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

# === 선택된 음식점 상세 정보 ===
if st.session_state.place_detail:
    _render_place_detail()

# === 키워드 결과 표시 ===
if st.session_state.scored_keywords:
    st.subheader("📊 추천 키워드 (점수 상위)")
    df = pd.DataFrame(st.session_state.scored_keywords)
    df.columns = ["키워드", "검색량", "경쟁도", "트렌드", "점수"]
    st.dataframe(df, use_container_width=True, hide_index=True)

# === 블로그 결과 표시 ===
if st.session_state.blog_result:
    _render_blog_result()

# === 해시태그 표시 ===
if st.session_state.hashtags:
    st.subheader("🏷 해시태그")
    hashtag_text = " ".join(st.session_state.hashtags)
    st.code(hashtag_text, language=None)
    st.button(
        "📋 해시태그 복사",
        key="copy_hashtags",
        on_click=lambda: _set_clipboard("hashtag", hashtag_text),
    )

# === 블로그 성장 대시보드 (사이드바 하단) ===
with st.sidebar:
    st.divider()
    with st.expander("📈 블로그 성장 대시보드", expanded=False):
        _render_advisor_dashboard()
