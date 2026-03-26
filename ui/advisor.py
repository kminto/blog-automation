"""
블로그 성장 대시보드 모듈
일일 루틴, 분석, 이웃 소통, 트렌드 등을 렌더링한다.
"""

import streamlit as st

from modules.blog_analytics import fetch_blog_stats, analyze_blog_growth
from modules.style_learner import crawl_my_blog, analyze_style, get_style_profile
from modules.blog_advisor import (
    get_trending_topics,
    get_neighbor_recommendations,
    generate_comment_templates,
    generate_weekly_plan,
    get_upcoming_topics,
    save_topic_plan,
    get_daily_routine,
)


def _run_routine_panel(routine_key: str):
    """각 루틴의 실행 패널을 표시한다."""

    if routine_key == "trend":
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
        st.markdown("---")
        st.info("왼쪽에서 음식점 검색 → 키워드 분석 → 본문 생성 후 완료 체크하세요")
        if st.button("✅ 글 발행 완료", key="done_write"):
            st.session_state["routine_done"]["write"] = True
            st.session_state["routine_open_write"] = False
            st.rerun()

    elif routine_key == "visit":
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
        st.markdown("---")
        st.markdown('[내 블로그 댓글 확인하기](https://blog.naver.com/rinx_x)')
        st.caption("새 댓글이 있으면 답글 달기 → 활동 지표 UP")
        if st.button("✅ 답글 완료", key="done_reply"):
            st.session_state["routine_done"]["reply"] = True
            st.session_state["routine_open_reply"] = False
            st.rerun()

    elif routine_key == "plan":
        st.markdown("---")
        plan = generate_weekly_plan()
        tomorrow = plan[1] if len(plan) > 1 else plan[0]
        st.markdown(f"**내일 추천 주제:** {tomorrow['theme']}")
        st.caption(f"발행 시간: {tomorrow['publish_time']} | 힌트: {tomorrow['keyword_hint']}")

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


def render_advisor_dashboard():
    """블로그 성장 대시보드를 렌더링한다."""

    # 내 블로그 분석
    if st.button("📊 내 블로그 분석", key="btn_my_blog"):
        st.session_state["show_analytics"] = True

    if st.session_state.get("show_analytics"):
        with st.spinner("블로그 데이터 수집 중..."):
            raw = fetch_blog_stats("rinx_x")
            analysis = analyze_blog_growth(raw)

        col1, col2, col3 = st.columns(3)
        col1.metric("총 포스팅", f"{analysis['total']}개")
        col2.metric("맛집 비율", f"{analysis['food_ratio']}%")
        col3.metric("월평균", f"{analysis['avg_per_month']}개")

        if analysis.get("latest_post"):
            st.caption(f"최근 글: {analysis['latest_post']['date']} | {analysis['latest_post']['title'][:30]}")
        if analysis.get("first_post"):
            st.caption(f"첫 글: {analysis['first_post']['date']}")

        monthly = analysis.get("monthly", {})
        if monthly:
            st.markdown("**월별 포스팅 추이**")
            chart_data = {k: v for k, v in monthly.items()}
            st.bar_chart(chart_data)

        st.markdown("**성장 진단**")
        for tip in analysis.get("diagnosis", []):
            st.markdown(f"{tip['icon']} **{tip['title']}** - {tip['detail']}")
            st.caption(f"→ {tip['action']}")

    st.markdown("---")

    # 일일 루틴
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

    st.markdown("---")

    # 내 말투 학습
    profile = get_style_profile()
    if profile:
        st.markdown(f"🧠 **말투 학습 완료** ({profile.get('sample_count', 0)}편 분석)")
        endings = [e[0] for e in profile.get("top_endings", [])[:4]]
        st.caption(f"주요 어미: {', '.join(endings)}")
    else:
        st.caption("🧠 말투 학습 전 (아래 버튼으로 학습)")

    if st.button("🧠 내 말투 학습하기", key="btn_learn_style"):
        with st.spinner("블로그 글 크롤링 중... (8편 수집)"):
            samples = crawl_my_blog("rinx_x", max_posts=8)
        if samples:
            with st.spinner("말투 패턴 분석 중..."):
                result = analyze_style(samples)
            st.success(f"학습 완료! {len(samples)}편 분석, {result.get('total_chars', 0):,}자")
            st.markdown("**분석 결과:**")
            endings = [f"{e[0]}({e[1]})" for e in result.get("top_endings", [])[:5]]
            st.caption(f"어미: {', '.join(endings)}")
            expressions = [f"{e[0]}({e[1]})" for e in result.get("top_expressions", [])[:5]]
            st.caption(f"감탄사: {', '.join(expressions)}")
            colloquials = [e[0] for e in result.get("top_colloquials", [])[:6]]
            st.caption(f"구어체: {', '.join(colloquials)}")
            st.caption(f"문장 평균: {result['sentence_stats']['avg_length']}자")
        else:
            st.error("블로그 글을 가져올 수 없습니다.")
