"""
블로그 생성 파이프라인 모듈
사진 분석 → 키워드 분석 → 본문 생성을 원클릭으로 실행한다.
"""

import streamlit as st

from modules.keyword_extractor import generate_keyword_combinations, filter_meaningful_keywords
from modules.naver_api import fetch_keyword_stats_batch
from modules.datalab_api import fetch_search_trend, analyze_trend
from modules.keyword_scorer import score_keyword, rank_keywords
from modules.blog_writer import generate_blog_post
from modules.hashtag_generator import generate_hashtags
from modules.blog_advisor import add_posting_record
from modules.keyword_cache import get_cached_keywords, save_to_cache, get_cache_stats
from modules.post_processor import get_ai_score
from modules.photo_analyzer import analyze_photos, build_photo_context, extract_menus_from_analysis
from utils.api_utils import safe_api_call


def _run_photo_analysis(status, progress, uploaded_photos: list) -> str:
    """사진 분석 단계. photo_context 문자열을 반환한다."""
    if not uploaded_photos:
        return ""

    status.update(label="📸 사진 AI 분석 중...")
    photo_data = [{"name": f.name, "bytes": f.read()} for f in uploaded_photos]
    # 파일 포인터 리셋
    for f in uploaded_photos:
        f.seek(0)

    result = safe_api_call(analyze_photos, photo_data)
    if result["success"]:
        st.session_state["photo_analysis"] = result["data"]
        detected = extract_menus_from_analysis(result["data"])
        status.write(f"📸 {len(result['data'])}장 분석 완료! 인식 메뉴: {', '.join(detected) if detected else '없음'}")
        progress.progress(15)
        return build_photo_context(result["data"])
    else:
        status.write(f"⚠️ 사진 분석 실패: {result['error']} (메모 기반으로 계속 진행)")
        progress.progress(15)
        return ""


def _run_keyword_analysis(status, progress, region_list: list[str], menu_list: list[str]):
    """키워드 분석 단계."""
    # 키워드 조합 생성
    status.update(label="🔍 키워드 조합 생성 중...")
    combinations = generate_keyword_combinations(region_list, menu_list)
    combinations = filter_meaningful_keywords(combinations)
    status.write(f"키워드 {len(combinations)}개 조합 생성")
    progress.progress(25)

    # 캐시 + API 조회
    status.update(label="🔍 네이버 API 조회 중...")
    cached_results, missed_keywords = get_cached_keywords(combinations)
    keyword_stats = list(cached_results)

    if missed_keywords:
        api_result = safe_api_call(fetch_keyword_stats_batch, missed_keywords)
        if api_result["success"]:
            keyword_stats.extend(api_result["data"])
            save_to_cache(api_result["data"])
            status.write(f"캐시 {len(cached_results)}개 + API {len(api_result['data'])}개")
        else:
            status.write(f"⚠️ API 오류: {api_result['error']}")
    else:
        status.write(f"캐시에서 {len(cached_results)}개 로드 (API 호출 없음)")
    progress.progress(45)

    # 트렌드 분석
    status.update(label="📈 트렌드 분석 중...")
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
    progress.progress(55)

    # 점수 계산
    status.update(label="🏆 키워드 점수 계산 중...")
    scored = []
    for kw_data in keyword_stats:
        keyword = kw_data.get("relKeyword", "")
        trend = trend_map.get(keyword, "유지")
        scored.append(score_keyword(kw_data, trend))
    ranked = rank_keywords(scored, regions=region_list, menus=menu_list)
    st.session_state.scored_keywords = ranked
    status.write(f"상위 {len(ranked)}개 키워드 선별 완료")
    progress.progress(60)


def _run_blog_generation(
    status, progress,
    restaurant_name: str, region_list: list[str], menu_list: list[str],
    companion: str, mood: str, memo: str,
    ordered_menus: str, my_review: str, photo_context: str,
):
    """본문 생성 단계."""
    # 메모 조합
    full_memo = memo
    if ordered_menus and ordered_menus.strip():
        full_memo += "\n\n[내가 주문한 메뉴]\n" + ordered_menus.strip()
    if my_review and my_review.strip():
        full_memo += "\n\n[내 솔직 후기]\n" + my_review.strip()

    # 본문 생성
    status.update(label="✍️ ChatGPT가 블로그 글을 작성 중...")
    status.write("gpt-4o 모델로 본문 생성 중... (10~20초)")
    result = safe_api_call(
        generate_blog_post,
        restaurant_name=restaurant_name,
        regions=region_list,
        menus=menu_list,
        companion=companion,
        mood=mood,
        memo=full_memo,
        top_keywords=st.session_state.scored_keywords,
        photo_context=photo_context,
    )
    if not result["success"]:
        status.update(label="본문 생성 오류", state="error")
        st.error(f"본문 생성 오류: {result['error']}")
        return False

    st.session_state.blog_result = result["data"]
    ai_check = get_ai_score(result["data"])
    grade_emoji = {"좋음": "🟢", "보통": "🟡", "개선필요": "🔴"}.get(ai_check["grade"], "⚪")
    status.write(f"본문 완료! {grade_emoji} AI 점수: {ai_check['score']}점 ({ai_check['grade']})")
    progress.progress(85)

    # 해시태그 생성
    status.update(label="🏷 해시태그 생성 중...")
    hashtag_list = generate_hashtags(
        restaurant_name=restaurant_name,
        regions=region_list,
        menus=menu_list,
        top_keywords=st.session_state.scored_keywords,
        mood=mood,
    )
    st.session_state.hashtags = hashtag_list
    progress.progress(95)

    # 기록 저장
    top_kws = [kw["keyword"] for kw in (st.session_state.scored_keywords or [])[:3]]
    add_posting_record(
        restaurant=restaurant_name,
        region=", ".join(region_list),
        keywords=top_kws,
        title=restaurant_name,
    )
    progress.progress(100)
    return True


def run_full_pipeline(
    restaurant_name: str,
    region_list: list[str],
    menu_list: list[str],
    companion: str,
    mood: str,
    memo: str,
    ordered_menus: str = "",
    my_review: str = "",
    uploaded_photos: list = None,
):
    """사진분석 → 키워드분석 → 본문생성 원클릭 파이프라인."""
    progress = st.progress(0)
    status = st.status("🚀 블로그 글 생성 시작...", expanded=True)

    has_photos = uploaded_photos and len(uploaded_photos) > 0
    total_steps = "사진분석 → 키워드분석 → 본문생성" if has_photos else "키워드분석 → 본문생성"
    status.write(f"진행: {total_steps}")

    # 1. 사진 분석 (있으면)
    photo_context = _run_photo_analysis(status, progress, uploaded_photos or [])

    # 2. 키워드 분석
    _run_keyword_analysis(status, progress, region_list, menu_list)

    # 3. 본문 생성
    success = _run_blog_generation(
        status, progress,
        restaurant_name, region_list, menu_list,
        companion, mood, memo,
        ordered_menus, my_review, photo_context,
    )

    if success:
        status.update(label="🎉 블로그 글 생성 완료!", state="complete")
        st.success("블로그 글 생성 완료! 아래에서 확인하세요.")
    else:
        status.update(label="❌ 생성 실패", state="error")
