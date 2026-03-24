"""
블로그 분석 모듈
네이버 블로그의 포스팅 히스토리, 성장 추이를 분석한다.
"""

import json
from collections import Counter
from urllib.parse import unquote

import requests


def fetch_blog_stats(blog_id: str = "rinx_x") -> dict:
    """네이버 블로그의 포스팅 히스토리를 가져온다."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36"
        ),
    }

    all_posts = []
    total_count = 0

    for page in range(1, 15):
        url = (
            f"https://blog.naver.com/PostTitleListAsync.naver"
            f"?blogId={blog_id}&currentPage={page}&countPerPage=10"
        )
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                break
            data = json.loads(r.text.replace("'", '"'))

            if page == 1:
                total_count = int(data.get("totalCount", 0))

            posts = data.get("postList", [])
            if not posts:
                break

            for p in posts:
                title = unquote(p.get("title", "").replace("+", " "))
                date = p.get("addDate", "").strip()
                all_posts.append({"date": date, "title": title})
        except Exception:
            break

    return {
        "blog_id": blog_id,
        "total_count": total_count,
        "posts": all_posts,
    }


def analyze_blog_growth(stats: dict) -> dict:
    """블로그 성장 추이를 분석한다."""
    posts = stats.get("posts", [])
    if not posts:
        return {"error": "포스팅 데이터 없음"}

    # 월별 포스팅 수
    monthly = Counter()
    for p in posts:
        date = p["date"]
        # "2025. 12. 19." → "2025.12"
        parts = date.replace(".", "").split()
        if len(parts) >= 2:
            ym = f"{parts[0]}.{parts[1].zfill(2)}"
            monthly[ym] = monthly.get(ym, 0) + 1

    # 카테고리 분석
    food_keywords = [
        "맛집", "후기", "메뉴", "치킨", "오마카세", "양꼬치",
        "국밥", "고기", "카페", "브런치", "술집", "리뷰",
        "맛있", "훠궈", "삼겹살", "데이트", "점심", "저녁",
    ]
    food_count = sum(
        1 for p in posts
        if any(kw in p["title"] for kw in food_keywords)
    )

    # 최근 활동도
    recent_dates = sorted(set(
        p["date"][:10].strip().rstrip(".")
        for p in posts
    ), reverse=True)

    # 첫 글 / 마지막 글
    first_post = posts[-1] if posts else None
    latest_post = posts[0] if posts else None

    # 월평균 포스팅
    month_count = len(monthly) if monthly else 1
    avg_per_month = round(len(posts) / month_count, 1)

    # 성장 진단
    diagnosis = _diagnose_growth(
        total=len(posts),
        monthly=monthly,
        food_ratio=food_count / len(posts) if posts else 0,
        avg_per_month=avg_per_month,
    )

    return {
        "total": len(posts),
        "monthly": dict(sorted(monthly.items())),
        "food_count": food_count,
        "food_ratio": round(food_count / len(posts) * 100) if posts else 0,
        "other_count": len(posts) - food_count,
        "avg_per_month": avg_per_month,
        "first_post": first_post,
        "latest_post": latest_post,
        "diagnosis": diagnosis,
    }


def _diagnose_growth(
    total: int,
    monthly: Counter,
    food_ratio: float,
    avg_per_month: float,
) -> list[dict]:
    """블로그 성장 진단 및 개선 포인트를 반환한다."""
    tips = []

    # 총 포스팅 수
    if total < 50:
        tips.append({
            "icon": "🔴",
            "title": "포스팅 수 부족",
            "detail": f"현재 {total}개. 최소 100개 이상이어야 C-Rank 안정",
            "action": "매일 1포스팅 목표!",
        })
    elif total < 200:
        tips.append({
            "icon": "🟡",
            "title": "포스팅 수 보통",
            "detail": f"현재 {total}개. 200개 넘기면 신뢰도 급상승",
            "action": "꾸준히 유지하세요",
        })
    else:
        tips.append({
            "icon": "🟢",
            "title": "포스팅 수 충분",
            "detail": f"현재 {total}개. 양보다 질에 집중할 때",
            "action": "체류시간 높은 글 위주로",
        })

    # 카테고리 집중도
    if food_ratio < 0.5:
        tips.append({
            "icon": "🔴",
            "title": "카테고리 분산",
            "detail": f"맛집 비율 {food_ratio*100:.0f}%. C-Rank는 한 분야 집중이 유리",
            "action": "맛집 글 비율을 70% 이상으로!",
        })
    elif food_ratio < 0.7:
        tips.append({
            "icon": "🟡",
            "title": "카테고리 집중 필요",
            "detail": f"맛집 비율 {food_ratio*100:.0f}%. 70% 이상이면 좋아요",
            "action": "다른 주제 줄이고 맛집에 집중",
        })
    else:
        tips.append({
            "icon": "🟢",
            "title": "카테고리 집중도 좋음",
            "detail": f"맛집 비율 {food_ratio*100:.0f}%",
            "action": "이대로 유지하세요!",
        })

    # 포스팅 빈도
    if avg_per_month < 5:
        tips.append({
            "icon": "🔴",
            "title": "포스팅 빈도 낮음",
            "detail": f"월 평균 {avg_per_month}개. 최소 주 3회 이상 권장",
            "action": "주 3~5회 포스팅으로 올리기",
        })
    elif avg_per_month < 15:
        tips.append({
            "icon": "🟡",
            "title": "포스팅 빈도 보통",
            "detail": f"월 평균 {avg_per_month}개",
            "action": "매일 1포스팅이면 파워블로거 궤도",
        })
    else:
        tips.append({
            "icon": "🟢",
            "title": "포스팅 빈도 좋음",
            "detail": f"월 평균 {avg_per_month}개",
            "action": "퀄리티 유지하며 꾸준히!",
        })

    # 최근 활동 공백
    sorted_months = sorted(monthly.keys(), reverse=True)
    if sorted_months:
        latest_month = sorted_months[0]
        # 현재 월과 비교
        from datetime import datetime
        current_ym = datetime.now().strftime("%Y.%m")
        if latest_month < current_ym:
            tips.append({
                "icon": "🔴",
                "title": "최근 활동 공백",
                "detail": f"마지막 포스팅 월: {latest_month}. 현재 {current_ym}",
                "action": "공백이 길면 C-Rank 하락! 지금 바로 글 쓰기",
            })

    return tips
