"""
블로그 성장 어드바이저 모듈
트렌드 기반 주제 추천, 포스팅 스케줄, 발행 체크리스트를 제공한다.
"""

import os
import json
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

POSTING_LOG_PATH = "data/posting_log.json"
TOPIC_PLAN_PATH = "data/topic_plan.json"
DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"


def _get_datalab_headers() -> dict:
    """데이터랩 API 헤더를 반환한다."""
    return {
        "X-Naver-Client-Id": os.getenv("NAVER_CLIENT_ID", ""),
        "X-Naver-Client-Secret": os.getenv("NAVER_CLIENT_SECRET", ""),
        "Content-Type": "application/json",
    }


# === 1. 트렌드 기반 주제 추천 ===

def get_trending_topics(base_region: str = "성남") -> list[dict]:
    """현재 시즌/트렌드에 맞는 맛집 주제를 추천한다."""
    now = datetime.now()
    month = now.month

    # 계절별 인기 키워드
    seasonal = {
        (12, 1, 2): ["뜨끈한국밥", "감자탕", "샤브샤브", "칼국수", "곱창"],
        (3, 4, 5): ["브런치", "파스타", "봄나들이맛집", "꽃놀이맛집", "피크닉"],
        (6, 7, 8): ["냉면", "초밥", "회", "빙수", "맥주맛집", "루프탑"],
        (9, 10, 11): ["갈비", "고기집", "와인바", "단풍맛집", "전골"],
    }

    season_keywords = []
    for months, keywords in seasonal.items():
        if month in months:
            season_keywords = keywords
            break

    # 상시 인기 키워드
    evergreen = ["데이트코스", "혼밥", "가성비맛집", "회식장소", "가족모임"]

    # 데이터랩으로 실시간 트렌드 확인
    trending = _check_datalab_trends(
        [f"{base_region} {kw}" for kw in season_keywords[:5]]
    )

    topics = []
    for kw in season_keywords:
        trend = trending.get(f"{base_region} {kw}", "유지")
        topics.append({
            "keyword": f"{base_region} {kw}",
            "type": "계절",
            "trend": trend,
            "priority": "높음" if trend == "상승" else "보통",
        })

    for kw in evergreen:
        topics.append({
            "keyword": f"{base_region} {kw}",
            "type": "상시",
            "trend": "유지",
            "priority": "보통",
        })

    # 상승 트렌드 우선 정렬
    topics.sort(key=lambda x: (
        0 if x["trend"] == "상승" else 1 if x["trend"] == "유지" else 2
    ))

    return topics


def _check_datalab_trends(keywords: list[str]) -> dict:
    """데이터랩에서 키워드 트렌드를 확인한다."""
    if not keywords:
        return {}

    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    body = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "timeUnit": "week",
        "keywordGroups": [
            {"groupName": kw, "keywords": [kw]}
            for kw in keywords[:5]
        ],
    }

    try:
        response = requests.post(
            DATALAB_URL,
            headers=_get_datalab_headers(),
            json=body,
            timeout=10,
        )
        if response.status_code != 200:
            return {}

        result = {}
        for item in response.json().get("results", []):
            data = item.get("data", [])
            if len(data) >= 4:
                recent = sum(d["ratio"] for d in data[-4:]) / 4
                prev = sum(d["ratio"] for d in data[-8:-4]) / 4 if len(data) >= 8 else recent
                if prev > 0:
                    rate = (recent - prev) / prev
                    if rate > 0.1:
                        result[item["title"]] = "상승"
                    elif rate < -0.1:
                        result[item["title"]] = "하락"
                    else:
                        result[item["title"]] = "유지"
        return result
    except Exception:
        return {}


# === 2. 포스팅 기록 관리 ===

def _ensure_data_dir():
    """data 디렉토리를 생성한다."""
    os.makedirs("data", exist_ok=True)


def load_posting_log() -> list[dict]:
    """포스팅 기록을 로드한다."""
    _ensure_data_dir()
    if not os.path.exists(POSTING_LOG_PATH):
        return []
    with open(POSTING_LOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_posting_log(log: list[dict]):
    """포스팅 기록을 저장한다."""
    _ensure_data_dir()
    with open(POSTING_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def add_posting_record(
    restaurant: str,
    region: str,
    keywords: list[str],
    title: str,
) -> dict:
    """포스팅 기록을 추가한다."""
    record = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "restaurant": restaurant,
        "region": region,
        "keywords": keywords,
        "title": title,
        "day_of_week": datetime.now().strftime("%A"),
    }
    log = load_posting_log()
    log.append(record)
    save_posting_log(log)
    return record


# === 3. 포스팅 통계 ===

def get_posting_stats() -> dict:
    """포스팅 통계를 반환한다."""
    log = load_posting_log()
    if not log:
        return {"total": 0, "message": "아직 포스팅 기록이 없습니다."}

    total = len(log)
    regions = {}
    keywords_used = {}

    for record in log:
        r = record.get("region", "미분류")
        regions[r] = regions.get(r, 0) + 1
        for kw in record.get("keywords", []):
            keywords_used[kw] = keywords_used.get(kw, 0) + 1

    # 최근 7일 포스팅 수
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    weekly = sum(1 for r in log if r["date"] >= week_ago)

    # 연속 포스팅 일수 계산
    dates = sorted(set(r["date"][:10] for r in log), reverse=True)
    streak = 0
    today = datetime.now().strftime("%Y-%m-%d")
    check_date = today
    for d in dates:
        if d == check_date:
            streak += 1
            check_date = (
                datetime.strptime(check_date, "%Y-%m-%d") - timedelta(days=1)
            ).strftime("%Y-%m-%d")
        else:
            break

    return {
        "total": total,
        "weekly": weekly,
        "streak": streak,
        "top_regions": sorted(regions.items(), key=lambda x: -x[1])[:5],
        "top_keywords": sorted(keywords_used.items(), key=lambda x: -x[1])[:10],
    }


# === 4. 발행 전 체크리스트 ===

def get_publish_checklist() -> list[dict]:
    """발행 전 확인할 체크리스트를 반환한다."""
    now = datetime.now()
    hour = now.hour

    # 골든타임 확인
    is_golden = (11 <= hour <= 12) or (17 <= hour <= 19)

    checklist = [
        {
            "item": "골든타임 발행",
            "detail": "점심(11~12시) 또는 저녁(17~19시)에 발행",
            "status": "good" if is_golden else "warn",
            "tip": f"현재 {hour}시 - {'골든타임!' if is_golden else '가능하면 골든타임에 발행 추천'}",
        },
        {
            "item": "제목 키워드 확인",
            "detail": "제목 앞쪽에 핵심 키워드가 있는지 확인",
            "status": "check",
            "tip": "예: '방이동맛집 우시야...'",
        },
        {
            "item": "사진 최소 10장",
            "detail": "사진이 충분한지 확인 (체류시간 증가)",
            "status": "check",
            "tip": "음식 사진은 다양한 각도로",
        },
        {
            "item": "본문 2000자 이상",
            "detail": "긴 글이 상위 노출에 유리",
            "status": "check",
            "tip": "메뉴별 상세 리뷰로 분량 확보",
        },
        {
            "item": "카테고리 설정",
            "detail": "맛집/음식 카테고리로 발행",
            "status": "check",
            "tip": "일관된 카테고리 = 높은 C-Rank",
        },
        {
            "item": "이웃 소통",
            "detail": "발행 후 다른 블로그 3~5개 방문 + 공감/댓글",
            "status": "check",
            "tip": "같은 카테고리 블로거와 소통하면 효과 UP",
        },
        {
            "item": "지도 첨부",
            "detail": "네이버 지도 위치 첨부 (검색 노출 가산)",
            "status": "check",
            "tip": "에디터에서 '장소' 버튼으로 추가",
        },
    ]

    return checklist


# === 5. 주간 콘텐츠 플랜 ===

def generate_weekly_plan(
    base_region: str = "성남",
    focus_category: str = "맛집",
) -> list[dict]:
    """주간 콘텐츠 플랜을 생성한다."""
    today = datetime.now()
    plan = []

    # 요일별 추천 콘텐츠 유형
    day_themes = {
        0: {"theme": "주말 방문 후기", "tip": "주말에 다녀온 곳 리뷰"},
        1: {"theme": "점심 맛집 추천", "tip": "직장인 점심 타겟"},
        2: {"theme": "가성비 맛집", "tip": "가성비 키워드 인기"},
        3: {"theme": "데이트/모임 맛집", "tip": "주말 계획하는 사람들 타겟"},
        4: {"theme": "술집/회식 맛집", "tip": "금요일 앞두고 술집 검색 증가"},
        5: {"theme": "브런치/카페", "tip": "주말 나들이 검색 피크"},
        6: {"theme": "특별한 맛집 (오마카세 등)", "tip": "주말 저녁 특별 식사 검색"},
    }

    for i in range(7):
        day = today + timedelta(days=i)
        weekday = day.weekday()
        theme = day_themes.get(weekday, {"theme": "자유 주제", "tip": ""})
        plan.append({
            "date": day.strftime("%m/%d (%a)"),
            "theme": theme["theme"],
            "tip": theme["tip"],
            "keyword_hint": f"{base_region} {theme['theme'].split()[0]}",
            "publish_time": "11:30" if weekday < 5 else "17:00",
        })

    return plan


# === 6. 소통 리마인더 + 추천 블로그 검색 ===

def get_neighbor_recommendations(region: str = "성남") -> list[dict]:
    """같은 지역 맛집 블로거를 네이버 블로그 검색으로 추천한다."""
    query = f"{region} 맛집 솔직후기"

    try:
        response = requests.get(
            "https://openapi.naver.com/v1/search/blog.json",
            headers={
                "X-Naver-Client-Id": os.getenv("NAVER_CLIENT_ID", ""),
                "X-Naver-Client-Secret": os.getenv("NAVER_CLIENT_SECRET", ""),
            },
            params={"query": query, "display": 10, "sort": "date"},
            timeout=10,
        )
        if response.status_code != 200:
            return []

        import re
        results = []
        seen_bloggers = set()
        for item in response.json().get("items", []):
            blogger = item.get("bloggername", "")
            if blogger in seen_bloggers:
                continue
            seen_bloggers.add(blogger)

            title = re.sub(r"<[^>]+>", "", item.get("title", ""))
            link = item.get("link", "")
            results.append({
                "blogger": blogger,
                "title": title,
                "link": link,
            })

        return results[:5]
    except Exception:
        return []


# === 7. 댓글 템플릿 자동 생성 ===

def generate_comment_templates(blog_title: str = "") -> list[str]:
    """상황별 댓글 템플릿을 생성한다. 복사해서 붙여넣기만 하면 됨."""
    import random

    # 공감형
    empathy = [
        "저도 여기 가보고 싶었는데 후기 감사해요! 사진 보니까 더 가고 싶어지네요 😊",
        "와 여기 분위기 진짜 좋아보여요~ 다음에 꼭 가봐야겠어요!",
        "사진이 너무 맛있어 보여요ㅠㅠ 저도 방문해봐야겠어요~",
        "꼼꼼한 리뷰 감사해요! 메뉴 고를 때 참고할게요 ㅎㅎ",
    ]

    # 질문형 (소통 유도)
    question = [
        "혹시 주차하기 편하셨나요? 차 가져갈까 고민 중이에요~",
        "웨이팅 있었나요? 주말에 가려고 하는데 궁금해요!",
        "여기 예약 필수인가요? 가보고 싶은데 팁 좀 주세요 ㅎㅎ",
        "혹시 아이들이랑 가기에도 괜찮을까요?",
    ]

    # 칭찬형
    praise = [
        "글 너무 잘 쓰시네요! 읽는 내내 군침 돌았어요 ㅎㅎ",
        "후기가 너무 생생해서 바로 예약하고 싶어졌어요!",
        "사진도 예쁘고 정보도 꼼꼼하고 최고예요~",
    ]

    # 경험 공유형
    share = [
        "저도 여기 다녀왔는데 정말 맛있었어요! 다음엔 다른 메뉴도 도전해보려고요~",
        "여기 진짜 숨은 맛집이죠! 저도 재방문 예정이에요 ㅎㅎ",
    ]

    all_templates = []
    all_templates.append({"type": "공감형", "text": random.choice(empathy)})
    all_templates.append({"type": "질문형", "text": random.choice(question)})
    all_templates.append({"type": "칭찬형", "text": random.choice(praise)})
    all_templates.append({"type": "경험공유형", "text": random.choice(share)})

    return all_templates


# === 8. 일일 루틴 체크리스트 ===

def get_daily_routine() -> list[dict]:
    """오늘의 블로그 운영 루틴을 생성한다."""
    now = datetime.now()
    hour = now.hour
    stats = get_posting_stats()

    routine = []

    # 오전 루틴
    routine.append({
        "time": "오전",
        "task": "트렌드 키워드 확인",
        "detail": "오늘 쓸 주제의 검색 트렌드 확인",
        "done": False,
        "minutes": 2,
    })

    # 글쓰기
    has_posted_today = False
    if stats["total"] > 0:
        log = load_posting_log()
        today_str = now.strftime("%Y-%m-%d")
        has_posted_today = any(r["date"].startswith(today_str) for r in log)

    routine.append({
        "time": "글쓰기",
        "task": "블로그 글 작성 + 발행",
        "detail": "골든타임(11~12시 또는 17~19시)에 발행",
        "done": has_posted_today,
        "minutes": 5,
    })

    # 소통 루틴
    routine.append({
        "time": "발행 후",
        "task": "이웃 블로그 3곳 방문",
        "detail": "같은 카테고리 블로거 방문 + 공감 + 댓글 1개씩",
        "done": False,
        "minutes": 5,
    })

    routine.append({
        "time": "발행 후",
        "task": "내 글에 달린 댓글 답글",
        "detail": "댓글이 있으면 반드시 답글 달기 (활동 지표)",
        "done": False,
        "minutes": 3,
    })

    # 저녁 루틴
    routine.append({
        "time": "저녁",
        "task": "내일 주제 정하기",
        "detail": "내일 갈 맛집 또는 리뷰할 곳 정하기",
        "done": False,
        "minutes": 2,
    })

    total_minutes = sum(r["minutes"] for r in routine)
    return {"routine": routine, "total_minutes": total_minutes}


# === 9. 내일 주제 저장/로드 ===

def save_topic_plan(topic: str, date: str = ""):
    """내일 쓸 주제를 저장한다."""
    _ensure_data_dir()
    if not date:
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    plans = _load_topic_plans()
    plans[date] = {
        "topic": topic,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "done": False,
    }
    with open(TOPIC_PLAN_PATH, "w", encoding="utf-8") as f:
        json.dump(plans, f, ensure_ascii=False, indent=2)


def get_today_topic() -> dict | None:
    """오늘 예정된 주제를 반환한다. (어제 저장한 것)"""
    plans = _load_topic_plans()
    today = datetime.now().strftime("%Y-%m-%d")
    return plans.get(today)


def get_upcoming_topics() -> list[dict]:
    """예정된 주제 목록을 반환한다."""
    plans = _load_topic_plans()
    today = datetime.now().strftime("%Y-%m-%d")
    upcoming = []
    for date, info in sorted(plans.items()):
        if date >= today:
            upcoming.append({"date": date, **info})
    return upcoming


def mark_topic_done(date: str):
    """해당 날짜 주제를 완료 처리한다."""
    plans = _load_topic_plans()
    if date in plans:
        plans[date]["done"] = True
        with open(TOPIC_PLAN_PATH, "w", encoding="utf-8") as f:
            json.dump(plans, f, ensure_ascii=False, indent=2)


def _load_topic_plans() -> dict:
    """주제 플랜 파일을 로드한다."""
    _ensure_data_dir()
    if not os.path.exists(TOPIC_PLAN_PATH):
        return {}
    with open(TOPIC_PLAN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
