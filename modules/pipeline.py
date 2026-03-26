"""
블로그 생성 파이프라인 모듈
키워드 분석과 본문 생성의 핵심 로직을 프로그레스 바와 함께 실행한다.
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
from utils.api_utils import safe_api_call


def run_keyword_analysis(region_list: list[str], menu_list: list[str]):
    """키워드 분석을 프로그레스 바와 함께 실행한다."""
    progress = st.progress(0)
    status = st.status("키워드 분석 시작...", expanded=True)

    # 1단계: 키워드 조합 생성 (25%)
    status.update(label="키워드 조합 생성 중...")
    combinations = generate_keyword_combinations(region_list, menu_list)
    combinations = filter_meaningful_keywords(combinations)
    status.write(f"총 {len(combinations)}개 키워드 조합 생성 완료")
    progress.progress(25)

    # 2단계: 캐시 확인 + 네이버 API 조회 (60%)
    status.update(label="캐시 확인 + API 조회 중...")
    cached_results, missed_keywords = get_cached_keywords(combinations)

    if cached_results:
        cache_stats = get_cache_stats()
        status.write(f"캐시 히트: {len(cached_results)}개 / API 필요: {len(missed_keywords)}개 (캐시 {cache_stats['valid']}개 보유)")

    keyword_stats = list(cached_results)

    if missed_keywords:
        batch_count = (len(missed_keywords) + 4) // 5
        status.write(f"네이버 API 배치 조회: {batch_count}개 배치")
        api_result = safe_api_call(fetch_keyword_stats_batch, missed_keywords)
        if not api_result["success"]:
            status.update(label="키워드 API 오류", state="error")
            st.error(f"키워드 API 오류: {api_result['error']}")
            progress.empty()
            return
        new_results = api_result["data"]
        keyword_stats.extend(new_results)
        # 캐시에 새 결과 저장
        save_to_cache(new_results)
        status.write(f"API 조회 완료: {len(new_results)}개 결과, 캐시 저장 완료")
    else:
        status.write("모든 키워드가 캐시에서 로드됨 (API 호출 없음)")

    progress.progress(60)

    # 3단계: 트렌드 분석 (80%)
    status.update(label="검색 트렌드 분석 중...")
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
    status.write(f"트렌드 분석 완료: {len(trend_map)}개 키워드")
    progress.progress(80)

    # 4단계: 점수 계산 (100%)
    status.update(label="키워드 점수 계산 중...")
    scored = []
    for kw_data in keyword_stats:
        keyword = kw_data.get("relKeyword", "")
        trend = trend_map.get(keyword, "유지")
        scored.append(score_keyword(kw_data, trend))
    ranked = rank_keywords(scored, regions=region_list, menus=menu_list)
    st.session_state.scored_keywords = ranked
    progress.progress(100)

    status.update(label="키워드 분석 완료!", state="complete")
    st.success(f"키워드 분석 완료! 상위 {len(ranked)}개 키워드 선별")


def run_blog_generation(
    restaurant_name: str,
    region_list: list[str],
    menu_list: list[str],
    companion: str,
    mood: str,
    memo: str,
    ordered_menus: str = "",
    my_review: str = "",
):
    """블로그 본문을 프로그레스 바와 함께 생성한다."""
    progress = st.progress(0)
    status = st.status("블로그 글 생성 시작...", expanded=True)

    # 메모 조합
    full_memo = memo
    if ordered_menus and ordered_menus.strip():
        full_memo += "\n\n[내가 주문한 메뉴]\n" + ordered_menus.strip()
    if my_review and my_review.strip():
        full_memo += "\n\n[내 솔직 후기]\n" + my_review.strip()

    # 1단계: 본문 생성 (50%)
    status.update(label="ChatGPT가 블로그 글을 작성하고 있습니다...")
    status.write("gpt-4o 모델로 본문 생성 중... (10~20초 소요)")
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
        status.update(label="본문 생성 오류", state="error")
        st.error(f"본문 생성 오류: {result['error']}")
        progress.empty()
        return
    st.session_state.blog_result = result["data"]
    status.write("본문 생성 완료!")
    progress.progress(50)

    # 2단계: 해시태그 생성 (80%)
    status.update(label="해시태그 생성 중...")
    hashtag_list = generate_hashtags(
        restaurant_name=restaurant_name,
        regions=region_list,
        menus=menu_list,
        top_keywords=st.session_state.scored_keywords,
        mood=mood,
    )
    st.session_state.hashtags = hashtag_list
    status.write(f"해시태그 {len(hashtag_list)}개 생성 완료")
    progress.progress(80)

    # 3단계: 기록 저장 (100%)
    status.update(label="포스팅 기록 저장 중...")
    top_kws = [kw["keyword"] for kw in (st.session_state.scored_keywords or [])[:3]]
    add_posting_record(
        restaurant=restaurant_name,
        region=", ".join(region_list),
        keywords=top_kws,
        title=restaurant_name,
    )
    progress.progress(100)

    status.update(label="블로그 글 생성 완료!", state="complete")
    st.success("블로그 글 생성 완료!")
