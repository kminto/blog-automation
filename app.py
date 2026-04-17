"""
맛집 블로그 자동화 시스템 - 메인 Streamlit 앱
여러 음식점 글을 목록으로 관리. 임시저장/불러오기/삭제.
"""

import streamlit as st
import pandas as pd

from modules.validators import validate_env
from modules.blog_advisor import get_today_topic
from modules.pipeline import run_full_pipeline
from modules.db import (
    is_db_available, save_draft, load_draft, list_drafts,
    delete_draft, restore_draft_to_session,
)
from ui.auth import check_authentication
from ui.search import render_sidebar_search, handle_search, render_search_results
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


def _init_session_state():
    """세션 상태를 초기화한다."""
    defaults = {
        "keyword_results": None,
        "scored_keywords": None,
        "blog_result": None,
        "hashtags": None,
        "search_results": None,
        "selected_place": None,
        "place_detail": None,
        "current_draft_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


_init_session_state()

# === 환경변수 검증 ===
missing_keys = validate_env()
if missing_keys:
    st.error(f"환경변수가 설정되지 않았습니다: {', '.join(missing_keys)}")
    st.info("`.env` 파일을 확인해주세요. `.env.example`을 참고하세요.")
    st.stop()


# === 사이드바 ===
with st.sidebar:
    # 임시저장 목록
    if is_db_available():
        st.header("📋 내 글 목록")

        # 새 글 작성 버튼
        if st.button("➕ 새 글 작성", use_container_width=True, key="btn_new_draft"):
            # 현재 작업 저장 (입력값이 있을 때만)
            if (st.session_state.get("place_detail")
                    and st.session_state.get("current_draft_id")
                    and st.session_state.get("input_ordered", "").strip()):
                save_draft(st.session_state["current_draft_id"], st.session_state)
            # 세션 초기화
            for key in [
                "keyword_results", "scored_keywords", "blog_result",
                "hashtags", "search_results", "selected_place", "place_detail",
                "current_draft_id", "expanded_inputs", "photo_analysis",
            ]:
                st.session_state[key] = None
            st.rerun()

        # 목록 표시
        drafts = list_drafts()
        if drafts:
            for d in drafts:
                name = d.get("restaurant_name", "제목 없음") or "제목 없음"
                region = d.get("regions", "") or ""
                has_result = "✅" if d.get("blog_result") else "✏️"
                updated = d.get("updated_at", "")[:10]

                col_name, col_del = st.columns([4, 1])
                with col_name:
                    if st.button(
                        f"{has_result} {name} ({region})",
                        key=f"draft_{d['id']}",
                        use_container_width=True,
                    ):
                        # 현재 작업 저장 (입력값이 있을 때만 - 빈 세션 덮어쓰기 방지)
                        if (st.session_state.get("place_detail")
                                and st.session_state.get("current_draft_id")
                                and st.session_state.get("input_ordered", "").strip()):
                            save_draft(st.session_state["current_draft_id"], st.session_state)
                        # 선택한 draft 복원
                        full_draft = load_draft(d["id"])
                        if full_draft:
                            restore_draft_to_session(full_draft)
                            st.session_state["current_draft_id"] = d["id"]
                            st.session_state["draft_restaurant_name"] = name
                            # place_detail 복원: 이름으로 최신 정보 자동 수집
                            if name != "제목 없음":
                                from modules.place_detail import fetch_place_detail as _fetch
                                fresh = _fetch(name=name)
                                if fresh:
                                    fresh["name"] = name
                                    st.session_state["place_detail"] = fresh
                                elif not st.session_state.get("place_detail"):
                                    st.session_state["place_detail"] = {
                                        "name": name, "road_address": "",
                                        "address": "", "category": "", "telephone": "",
                                    }
                        st.rerun()
                with col_del:
                    if st.button("🗑", key=f"del_{d['id']}"):
                        delete_draft(d["id"])
                        if st.session_state.get("current_draft_id") == d["id"]:
                            st.session_state["current_draft_id"] = None
                        st.rerun()

            st.caption(f"총 {len(drafts)}개 글")
        else:
            st.caption("저장된 글이 없어요. 음식점 검색으로 시작하세요!")

        st.divider()

    # 음식점 검색
    search_query, btn_search, btn_reset = render_sidebar_search()

    # 대시보드
    st.divider()
    with st.expander("📈 블로그 성장 대시보드", expanded=False):
        render_advisor_dashboard()


# === 초기화 ===
if btn_reset:
    if (st.session_state.get("current_draft_id")
            and st.session_state.get("input_ordered", "").strip()):
        save_draft(st.session_state["current_draft_id"], st.session_state)
    for key in [
        "keyword_results", "scored_keywords", "blog_result",
        "hashtags", "search_results", "selected_place", "place_detail",
        "current_draft_id", "expanded_inputs", "photo_analysis",
    ]:
        st.session_state[key] = None
    st.rerun()

if btn_search and search_query:
    handle_search(search_query)

# === 메인 영역 ===

# 오늘 예정된 주제 알림
_today_topic = get_today_topic()
if _today_topic and not _today_topic.get("done"):
    st.markdown(
        f'<div style="background:#fff3cd;border-left:4px solid #ff9800;'
        f'padding:12px 16px;border-radius:4px;margin-bottom:12px;">'
        f'📌 <b>오늘의 주제:</b> {_today_topic["topic"]}</div>',
        unsafe_allow_html=True,
    )

# 검색 결과
if st.session_state.search_results and not st.session_state.selected_place:
    render_search_results()
elif not st.session_state.get("place_detail"):
    st.markdown("#### 🍽️ 맛집 블로그 자동화")
    st.caption("사이드바에서 음식점을 검색하거나, 목록에서 글을 선택하세요.")

# 선택된 음식점
if st.session_state.place_detail:
    # 새 음식점이면 draft ID 생성
    if not st.session_state.get("current_draft_id") and is_db_available():
        new_id = save_draft("", st.session_state)
        st.session_state["current_draft_id"] = new_id

    render_place_detail(
        on_analyze=None,
        on_generate=run_full_pipeline,
    )

    # 키워드 결과
    if st.session_state.scored_keywords:
        with st.expander(f"📊 키워드 분석 ({len(st.session_state.scored_keywords)}개)", expanded=False):
            display_data = [
                {
                    "키워드": kw.get("keyword", ""),
                    "검색량": kw.get("search_volume", 0),
                    "경쟁도": kw.get("competition", ""),
                    "트렌드": kw.get("trend", ""),
                    "점수": kw.get("score", 0),
                }
                for kw in st.session_state.scored_keywords
            ]
            df = pd.DataFrame(display_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

    # 블로그 결과
    if st.session_state.blog_result:
        render_blog_result()

# === DB 자동 저장 ===
if is_db_available() and st.session_state.get("place_detail"):
    draft_id = st.session_state.get("current_draft_id", "")
    # 빈 세션 덮어쓰기 방지: draft가 이미 있으면 입력값 있을 때만 업데이트
    if draft_id:
        has_any_input = any(
            st.session_state.get(k, "").strip()
            for k in ["input_ordered", "input_companion", "input_visit_reason",
                       "sd_taste", "input_mood", "pr_revisit"]
        )
        if has_any_input:
            save_draft(draft_id, st.session_state)
    else:
        # 새 음식점 → 무조건 생성 (목록에 바로 표시)
        saved_id = save_draft("", st.session_state)
        if saved_id:
            st.session_state["current_draft_id"] = saved_id
