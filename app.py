"""
맛집 블로그 자동화 시스템 - 메인 Streamlit 앱
UI 컴포넌트를 조합하여 전체 워크플로우를 오케스트레이션한다.
Supabase DB로 작성 중인 글 자동 저장/복원.
"""

import streamlit as st
import pandas as pd

from modules.validators import validate_env
from modules.blog_advisor import get_today_topic
from modules.pipeline import run_full_pipeline
from modules.db import is_db_available, save_draft, load_draft, clear_draft
from ui.auth import check_authentication
from ui.search import render_sidebar_search, handle_reset, handle_search, render_search_results
from ui.place_detail import render_place_detail
from ui.blog_result import render_blog_result
from ui.advisor import render_advisor_dashboard
from ui.helpers import set_clipboard

# === 페이지 설정 ===
st.set_page_config(
    page_title="맛집 블로그 자동화",
    page_icon="🍽️",
    layout="wide",
)

# === 비밀번호 잠금 ===
if not check_authentication():
    st.stop()

st.markdown("#### 개인 테스트 프로그램 만들기")

# === 오늘 예정된 주제 알림 ===
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


def _init_session_state():
    """세션 상태를 초기화한다. DB에 저장된 draft가 있으면 복원."""
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

    # DB에서 작성 중인 글 복원 (최초 1회)
    if "draft_loaded" not in st.session_state and is_db_available():
        draft = load_draft()
        if draft and draft.get("restaurant_name"):
            # 텍스트 필드 복원
            restore_map = {
                "input_regions": "regions",
                "input_menus": "menus",
                "input_ordered": "ordered_menus",
                "review_best": "review_best",
                "review_worst": "review_worst",
                "review_episode": "review_episode",
                "input_companion": "companion",
                "input_mood": "mood",
                "input_memo": "memo",
                "review_vibe": "review_vibe",
                "review_cook": "review_cook",
                "review_wait": "review_wait",
                "review_revisit": "review_revisit",
            }
            for session_key, db_key in restore_map.items():
                if draft.get(db_key):
                    st.session_state[session_key] = draft[db_key]

            # JSON 필드 복원
            if draft.get("scored_keywords"):
                st.session_state["scored_keywords"] = draft["scored_keywords"]
            if draft.get("blog_result"):
                st.session_state["blog_result"] = draft["blog_result"]
            if draft.get("hashtags"):
                st.session_state["hashtags"] = draft["hashtags"]
            if draft.get("expanded_inputs"):
                st.session_state["expanded_inputs"] = draft["expanded_inputs"]
            if draft.get("photo_analysis"):
                st.session_state["photo_analysis"] = draft["photo_analysis"]

            st.session_state["draft_restaurant_name"] = draft["restaurant_name"]

        st.session_state["draft_loaded"] = True


_init_session_state()

# === 환경변수 검증 ===
missing_keys = validate_env()
if missing_keys:
    st.error(f"환경변수가 설정되지 않았습니다: {', '.join(missing_keys)}")
    st.info("`.env` 파일을 확인해주세요. `.env.example`을 참고하세요.")
    st.stop()

# DB 상태 표시
if is_db_available():
    restored_name = st.session_state.get("draft_restaurant_name", "")
    if restored_name:
        st.caption(f"💾 이전 작성 중: **{restored_name}** (자동 복원됨)")
else:
    st.caption("⚠️ DB 미연결 - 새로고침 시 데이터 유실")

# === 사이드바: 음식점 검색 ===
with st.sidebar:
    search_query, btn_search, btn_reset = render_sidebar_search()

if btn_reset:
    clear_draft()
    handle_reset()

if btn_search and search_query:
    handle_search(search_query)

# === 검색 결과 표시 및 선택 ===
if st.session_state.search_results and not st.session_state.selected_place:
    render_search_results()

# === 선택된 음식점 상세 정보 ===
if st.session_state.place_detail:
    render_place_detail(
        on_analyze=None,
        on_generate=run_full_pipeline,
    )

# === 키워드 결과 표시 ===
if st.session_state.scored_keywords:
    st.subheader("📊 추천 키워드 (점수 상위)")
    df = pd.DataFrame(st.session_state.scored_keywords)
    df.columns = ["키워드", "검색량", "경쟁도", "트렌드", "점수"]
    st.dataframe(df, use_container_width=True, hide_index=True)

# === 블로그 결과 표시 ===
if st.session_state.blog_result:
    render_blog_result()

# === 해시태그 표시 ===
if st.session_state.hashtags:
    st.subheader("🏷 해시태그")
    hashtag_text = " ".join(st.session_state.hashtags)
    st.code(hashtag_text, language=None)
    st.button(
        "📋 해시태그 복사",
        key="copy_hashtags",
        on_click=lambda: set_clipboard("hashtag", hashtag_text),
    )

# === 블로그 성장 대시보드 (사이드바 하단) ===
with st.sidebar:
    st.divider()
    with st.expander("📈 블로그 성장 대시보드", expanded=False):
        render_advisor_dashboard()

# === DB 자동 저장 (매 렌더링마다) ===
if is_db_available():
    save_draft(st.session_state)
