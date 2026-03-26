"""
Supabase DB 연동 모듈
여러 음식점 글을 목록으로 관리. 임시저장/불러오기/삭제.
"""

import json
import os
from datetime import datetime

import streamlit as st

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


def _get_client() -> "Client":
    """Supabase 클라이언트를 생성한다."""
    if not SUPABASE_AVAILABLE:
        return None

    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
    key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY", ""))

    if not url or not key:
        return None

    return create_client(url, key)


def is_db_available() -> bool:
    """DB 사용 가능 여부를 확인한다."""
    return _get_client() is not None


# === 작성 중인 글 목록 관리 ===

def save_draft(draft_id: str, session_state: dict) -> str:
    """작성 중인 글을 DB에 저장한다. 새 글이면 ID를 생성한다."""
    client = _get_client()
    if not client:
        return draft_id

    data = {"updated_at": datetime.now().isoformat()}

    if draft_id:
        data["id"] = draft_id

    # 음식점 이름
    place = session_state.get("place_detail")
    if isinstance(place, dict):
        data["restaurant_name"] = place.get("name", "")
    else:
        data["restaurant_name"] = str(place) if place else ""

    # 텍스트 필드
    field_map = {
        "regions": "input_regions",
        "menus": "input_menus",
        "ordered_menus": "input_ordered",
        "review_best": "review_best",
        "review_worst": "review_worst",
        "review_episode": "review_episode",
        "companion": "input_companion",
        "mood": "input_mood",
        "memo": "input_memo",
        "review_vibe": "review_vibe",
        "review_cook": "review_cook",
        "review_wait": "review_wait",
        "review_revisit": "review_revisit",
    }
    for db_field, session_key in field_map.items():
        value = session_state.get(session_key, "")
        data[db_field] = str(value) if value else ""

    # JSON 필드
    for field in ["expanded_inputs", "scored_keywords", "hashtags", "photo_analysis"]:
        value = session_state.get(field)
        if value:
            data[field] = json.loads(json.dumps(value, default=str))
        else:
            data[field] = None

    data["blog_result"] = session_state.get("blog_result", "")

    try:
        result = client.table("drafts").upsert(data).execute()
        if result.data:
            return result.data[0].get("id", draft_id)
    except Exception:
        pass

    return draft_id


def load_draft(draft_id: str) -> dict:
    """특정 draft를 불러온다."""
    client = _get_client()
    if not client:
        return {}

    try:
        result = client.table("drafts").select("*").eq("id", draft_id).execute()
        if result.data:
            return result.data[0]
    except Exception:
        pass

    return {}


def list_drafts() -> list[dict]:
    """모든 임시저장 글 목록을 반환한다."""
    client = _get_client()
    if not client:
        return []

    try:
        result = client.table("drafts") \
            .select("id, restaurant_name, regions, menus, blog_result, updated_at") \
            .order("updated_at", desc=True) \
            .limit(20) \
            .execute()
        return result.data or []
    except Exception:
        return []


def delete_draft(draft_id: str):
    """임시저장 글을 삭제한다."""
    client = _get_client()
    if not client:
        return

    try:
        client.table("drafts").delete().eq("id", draft_id).execute()
    except Exception:
        pass


def restore_draft_to_session(draft: dict):
    """draft 데이터를 세션 상태에 복원한다."""
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
    for field in ["scored_keywords", "blog_result", "hashtags", "expanded_inputs", "photo_analysis"]:
        if draft.get(field):
            st.session_state[field] = draft[field]
        else:
            st.session_state[field] = None


# === 포스팅 기록 ===

def save_posting_record(restaurant: str, region: str, keywords: list, title: str):
    """포스팅 기록을 DB에 저장한다."""
    client = _get_client()
    if not client:
        return

    try:
        client.table("posting_log").insert({
            "restaurant": restaurant,
            "region": region,
            "keywords": keywords,
            "title": title,
        }).execute()
    except Exception:
        pass


# === 말투 프로필 ===

def save_style_profile(profile: dict):
    """말투 프로필을 DB에 저장한다."""
    client = _get_client()
    if not client:
        return

    try:
        client.table("style_profile").upsert({
            "id": "main",
            "profile": profile,
            "updated_at": datetime.now().isoformat(),
        }).execute()
    except Exception:
        pass


def load_style_profile() -> dict:
    """DB에서 말투 프로필을 불러온다."""
    client = _get_client()
    if not client:
        return {}

    try:
        result = client.table("style_profile").select("*").eq("id", "main").execute()
        if result.data:
            return result.data[0].get("profile", {})
    except Exception:
        pass

    return {}
