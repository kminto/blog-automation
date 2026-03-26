"""
Supabase DB 연동 모듈
작성 중인 글 자동 저장/불러오기, 포스팅 기록, 말투 프로필 관리.
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

    # Streamlit secrets 또는 환경변수에서 가져오기
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
    key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY", ""))

    if not url or not key:
        return None

    return create_client(url, key)


def is_db_available() -> bool:
    """DB 사용 가능 여부를 확인한다."""
    return _get_client() is not None


# === 작성 중인 글 저장/불러오기 ===

DRAFT_FIELDS = [
    "restaurant_name", "regions", "menus", "ordered_menus",
    "review_best", "review_worst", "review_episode",
    "companion", "mood", "memo",
    "review_vibe", "review_cook", "review_wait", "review_revisit",
]

DRAFT_JSON_FIELDS = [
    "expanded_inputs", "scored_keywords", "hashtags", "photo_analysis",
]


def save_draft(session_state: dict):
    """작성 중인 글을 DB에 저장한다."""
    client = _get_client()
    if not client:
        return

    data = {"id": "current", "updated_at": datetime.now().isoformat()}

    # 텍스트 필드
    field_to_session = {
        "restaurant_name": "place_detail",
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

    for db_field, session_key in field_to_session.items():
        value = session_state.get(session_key, "")
        if db_field == "restaurant_name" and isinstance(value, dict):
            value = value.get("name", "")
        data[db_field] = str(value) if value else ""

    # JSON 필드
    for field in DRAFT_JSON_FIELDS:
        value = session_state.get(field) or session_state.get(f"_{field}")
        if value:
            data[field] = json.loads(json.dumps(value, default=str))
        else:
            data[field] = None

    # blog_result
    data["blog_result"] = session_state.get("blog_result", "")

    try:
        client.table("drafts").upsert(data).execute()
    except Exception:
        pass  # 저장 실패해도 앱은 계속 동작


def load_draft() -> dict:
    """저장된 작성 중 글을 불러온다."""
    client = _get_client()
    if not client:
        return {}

    try:
        result = client.table("drafts").select("*").eq("id", "current").execute()
        if result.data:
            return result.data[0]
    except Exception:
        pass

    return {}


def clear_draft():
    """작성 중인 글을 초기화한다."""
    client = _get_client()
    if not client:
        return

    try:
        client.table("drafts").delete().eq("id", "current").execute()
    except Exception:
        pass


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


def get_posting_records(limit: int = 20) -> list:
    """포스팅 기록을 불러온다."""
    client = _get_client()
    if not client:
        return []

    try:
        result = client.table("posting_log") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        return result.data or []
    except Exception:
        return []


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
