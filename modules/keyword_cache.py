"""
키워드 캐싱 모듈
네이버 키워드도구 API 결과를 로컬 JSON에 캐싱하여 중복 호출을 방지한다.
TTL: 7일 (검색량은 급변하지 않으므로 충분)
"""

import json
import os
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CACHE_FILE = os.path.join(DATA_DIR, "keyword_cache.json")
CACHE_TTL_DAYS = 14  # 검색량은 급변하지 않으므로 2주


def _load_cache() -> dict:
    """캐시 파일을 로드한다."""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict):
    """캐시 파일을 저장한다."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _is_expired(cached_at: str) -> bool:
    """캐시 항목이 만료되었는지 확인한다."""
    try:
        cached_time = datetime.fromisoformat(cached_at)
        return datetime.now() - cached_time > timedelta(days=CACHE_TTL_DAYS)
    except (ValueError, TypeError):
        return True


def _normalize_keyword(keyword: str) -> str:
    """키워드를 정규화한다 (공백 제거, 소문자)."""
    return keyword.replace(" ", "").lower()


def get_cached_keywords(keywords: list[str]) -> tuple[list[dict], list[str]]:
    """캐시에서 키워드를 조회한다.

    Returns:
        (cached_results, missed_keywords): 캐시 히트 결과와 미스된 키워드 목록
    """
    cache = _load_cache()
    cached_results = []
    missed = []

    for kw in keywords:
        normalized = _normalize_keyword(kw)
        entry = cache.get(normalized)

        if entry and not _is_expired(entry.get("cached_at", "")):
            cached_results.append(entry["data"])
        else:
            missed.append(kw)

    return cached_results, missed


def save_to_cache(api_results: list[dict]):
    """API 결과를 캐시에 저장한다."""
    cache = _load_cache()
    now = datetime.now().isoformat()

    for item in api_results:
        keyword = item.get("relKeyword", "")
        if not keyword:
            continue
        normalized = _normalize_keyword(keyword)
        cache[normalized] = {
            "data": item,
            "cached_at": now,
        }

    # 만료된 항목 정리
    expired_keys = [
        k for k, v in cache.items()
        if _is_expired(v.get("cached_at", ""))
    ]
    for k in expired_keys:
        del cache[k]

    _save_cache(cache)


def get_cache_stats() -> dict:
    """캐시 통계를 반환한다."""
    cache = _load_cache()
    total = len(cache)
    valid = sum(1 for v in cache.values() if not _is_expired(v.get("cached_at", "")))
    return {"total": total, "valid": valid, "expired": total - valid}
