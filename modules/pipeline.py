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
from modules.seo_validator import run_seo_validation
from modules.engagement_optimizer import validate_engagement
from modules.publish_scheduler import recommend_publish_time
from modules.series_planner import suggest_series, find_related_posts, build_internal_link_prompt
from modules.competitor_analyzer import get_competitive_guide, build_competitor_prompt
from modules.photo_analyzer import analyze_photos, build_photo_context, extract_menus_from_analysis
from modules.post_processor import process_blog_text
from utils.api_utils import safe_api_call


def _grade_emoji(grade: str, mode: str = "ai") -> str:
    """등급별 이모지를 반환한다."""
    if mode == "seo":
        return {"A": "🟢", "B": "🟡", "C": "🔴"}.get(grade, "⚪")
    return {"좋음": "🟢", "보통": "🟡", "개선필요": "🔴"}.get(grade, "⚪")


def _revise_blog_text(original_text: str, feedback: str) -> str:
    """1차 본문을 피드백 기반으로 직접 수정한다."""
    import os
    from openai import OpenAI
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=4096,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 블로그 글을 수정하는 편집자입니다. "
                        "원본 글의 말투와 구조를 유지하면서 피드백만 반영하세요. "
                        "새로운 내용을 지어내지 말고, 기존 내용을 보강/확장만 하세요. "
                        "~합니다 금지, ~했어요/~더라고요 유지."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""아래 블로그 글을 피드백에 따라 수정해주세요.
원본 글의 말투/톤/구조를 그대로 유지하면서 부족한 부분만 보강하세요.

[원본 글]
{original_text}

[수정 피드백 - 모두 반영할 것]
{feedback}

[규칙]
- 원본 글의 문체/어미를 그대로 유지
- "출처 입력" + "사진 설명을 입력하세요." 사진 자리 유지
- 본문만 출력 (제목/해시태그 제외)
- 마크다운(**, ##, ---) 사용 금지
- 해시태그 넣지 말 것
- 1~2문장마다 반드시 줄바꿈 (빈 줄 삽입)
- 3문장 이상 연속으로 이어지는 문단 금지
- 전체 1500~2000자 필수 (부족하면 메뉴 묘사, 반찬 리뷰, 총평을 확장)
- 질문형 문장 2개 이상 필수 (예: '혹시 ~해보신 분?', '어떤 메뉴가 끌리세요?')""",
                },
            ],
        )
        revised = response.choices[0].message.content
        # 거부 응답 감지
        if any(p in revised[:50] for p in ["죄송", "처리할 수 없"]):
            return ""
        return process_blog_text(revised)
    except Exception:
        return ""


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


def _run_keyword_analysis(
    status, progress, region_list: list[str], menu_list: list[str],
    user_context: str = "",
):
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

    # 트렌드 분석 (상위 3개만 - 속도 최적화)
    status.update(label="📈 트렌드 분석 중...")
    top_for_trend = sorted(
        keyword_stats,
        key=lambda x: (
            (x.get("monthlyPcQcCnt", 0) if isinstance(x.get("monthlyPcQcCnt", 0), int) else 5)
            + (x.get("monthlyMobileQcCnt", 0) if isinstance(x.get("monthlyMobileQcCnt", 0), int) else 5)
        ),
        reverse=True,
    )[:3]  # 5개 → 3개로 축소
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
    # place_detail의 카테고리로 무관한 키워드 필터링 (카페/놀거리 등 제외)
    place_category = ""
    if st.session_state.get("place_detail"):
        place_category = st.session_state["place_detail"].get("category", "맛집")
    ranked = rank_keywords(
        scored, regions=region_list, menus=menu_list,
        category=place_category or "맛집",
        user_context=user_context,
    )
    st.session_state.scored_keywords = ranked
    status.write(f"상위 {len(ranked)}개 키워드 선별 완료")
    progress.progress(60)


def _run_blog_generation(
    status, progress,
    restaurant_name: str, region_list: list[str], menu_list: list[str],
    companion: str, mood: str, memo: str,
    ordered_menus: str, my_review: str, photo_context: str,
    place_detail: dict = None,
    detailed_review: dict = None,
    visit_reason: str = "",
):
    """본문 생성 단계."""
    # 메모 조합
    full_memo = memo
    if ordered_menus and ordered_menus.strip():
        full_memo += "\n\n[내가 주문한 메뉴]\n" + ordered_menus.strip()
    if my_review and my_review.strip():
        full_memo += "\n\n[내 솔직 후기]\n" + my_review.strip()

    # 시리즈/내부 링크 정보 수집 (경쟁분석 API 호출 제거 → 속도 개선)
    extra_context = ""
    try:
        from modules.blog_advisor import load_posting_log
        posting_log = load_posting_log()
        related = find_related_posts(
            region_list[0] if region_list else "",
            "맛집", posting_log,
            exclude_restaurant=restaurant_name,
        )
        if related:
            link_prompt = build_internal_link_prompt(related)
            extra_context += f"\n{link_prompt}"

        series = suggest_series(region_list[0] if region_list else "", posting_log)
        if series.get("has_series"):
            extra_context += f"\n[시리즈] {series['series_name']}"
    except Exception:
        pass

    if extra_context:
        full_memo += f"\n\n{extra_context}"

    # 1차 본문 생성
    status.update(label="✍️ 본문 생성 중...")
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
        place_detail=place_detail,
        detailed_review=detailed_review,
        visit_reason=visit_reason,
    )
    if not result["success"]:
        status.update(label="본문 생성 오류", state="error")
        st.error(f"본문 생성 오류: {result['error']}")
        return False

    blog_text = result["data"]
    progress.progress(75)

    # 품질 검증
    status.update(label="🔍 품질 검증 중...")
    ai_check = get_ai_score(blog_text)
    seo_result = run_seo_validation(blog_text, st.session_state.scored_keywords)
    engage_result = validate_engagement(blog_text)

    status.write(f"AI 냄새 {_grade_emoji(ai_check['grade'])} {ai_check['score']}점")
    status.write(f"SEO {_grade_emoji(seo_result['grade'], 'seo')} {seo_result['score']}점")
    status.write(f"체류시간 {_grade_emoji(engage_result['grade'], 'seo')} {engage_result['score']}점")

    # 품질 통과 판정
    quality_pass = (
        seo_result["grade"] in ("A", "B")
        and ai_check["grade"] in ("좋음", "보통")
        and engage_result["grade"] in ("A", "B")
    )

    if not quality_pass:
        # 피드백 수집
        feedback_lines = []
        for issue in seo_result.get("issues", []):
            feedback_lines.append(issue)
        for sug in engage_result.get("suggestions", []):
            feedback_lines.append(sug)
        if ai_check["grade"] == "개선필요":
            feedback_lines.append("AI 냄새 제거: 격식체(합니다/됩니다)→구어체(해요/더라고요), 과장 표현 제거")

        if feedback_lines:
            status.write("🔄 품질 미달 → 1차 본문 기반으로 개선 중...")
            progress.progress(80)

            # 1차 본문 + 피드백으로 직접 수정 요청 (새로 생성이 아닌 수정)
            feedback_text = "\n".join(f"- {line}" for line in feedback_lines)
            revision_result = _revise_blog_text(blog_text, feedback_text)

            if revision_result:
                blog_text = revision_result

                # 재검증
                ai_check = get_ai_score(blog_text)
                seo_result = run_seo_validation(blog_text, st.session_state.scored_keywords)
                engage_result = validate_engagement(blog_text)

                status.write(f"개선 후: AI {_grade_emoji(ai_check['grade'])} / "
                             f"SEO {_grade_emoji(seo_result['grade'], 'seo')} / "
                             f"체류 {_grade_emoji(engage_result['grade'], 'seo')}")

                # 재검증 후에도 미달이면 부족한 입력 안내
                still_issues = seo_result.get("issues", []) + engage_result.get("suggestions", [])
                if still_issues:
                    for issue in still_issues[:3]:
                        status.write(f"  ⚠️ {issue}")
            else:
                status.write("⚠️ 개선 재생성 실패 → 1차 본문 사용")

    progress.progress(85)

    # 최종 결과 저장
    st.session_state.blog_result = blog_text
    st.session_state["seo_validation"] = seo_result
    st.session_state["engagement"] = engage_result
    progress.progress(88)

    # 발행 타이밍 추천
    pub_time = recommend_publish_time(st.session_state.scored_keywords, restaurant_name)
    st.session_state["publish_time"] = pub_time
    status.write(f"📅 추천 발행: {pub_time['best_time']} ({pub_time['reason']})")
    progress.progress(90)

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
    place_detail: dict = None,
    detailed_review: dict = None,
    visit_reason: str = "",
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
    # 사용자 입력 전체를 컨텍스트로 조합 (키워드 필터링에 사용)
    user_context = " ".join([
        companion or "", mood or "", memo or "",
        ordered_menus or "", my_review or "", visit_reason or "",
    ])
    _run_keyword_analysis(status, progress, region_list, menu_list, user_context)

    # 3. 본문 생성
    # place_detail 자동 수집 (세션에 없으면)
    if place_detail is None:
        place_detail = st.session_state.get("place_detail")
    if place_detail is None:
        from modules.place_detail import fetch_place_detail
        status.update(label="📍 운영정보 자동 수집 중...")
        place_detail = fetch_place_detail(name=restaurant_name)
        if place_detail:
            st.session_state["place_detail"] = place_detail
            status.write(f"📍 운영정보 수집 완료: {place_detail.get('business_hours', '미확인')}")

    success = _run_blog_generation(
        status, progress,
        restaurant_name, region_list, menu_list,
        companion, mood, memo,
        ordered_menus, my_review, photo_context,
        place_detail=place_detail,
        detailed_review=detailed_review,
        visit_reason=visit_reason,
    )

    if success:
        status.update(label="🎉 블로그 글 생성 완료!", state="complete")
        st.success("블로그 글 생성 완료! 아래에서 확인하세요.")
    else:
        status.update(label="❌ 생성 실패", state="error")
