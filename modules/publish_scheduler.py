"""
발행 타이밍 최적화 모듈
키워드 유형별 최적 발행 시간을 추천한다.
"""

from datetime import datetime


# 키워드 유형별 최적 발행 시간 (네이버 검색 패턴 기반)
PUBLISH_WINDOWS = {
    "점심": {
        "keywords": ["점심", "런치", "브런치", "국밥", "백반", "칼국수"],
        "best_time": "10:00~10:30",
        "reason": "점심 검색 피크(11:30~12:30) 1~2시간 전 발행 → 인덱싱 완료 후 노출",
    },
    "저녁": {
        "keywords": ["저녁", "회식", "술집", "고기", "삼겹살", "이자카야"],
        "best_time": "15:00~16:00",
        "reason": "퇴근 전 저녁 맛집 검색(17~18시) 전 발행",
    },
    "카페": {
        "keywords": ["카페", "디저트", "브런치", "빵", "케이크"],
        "best_time": "09:00~10:00",
        "reason": "오전~점심 카페 검색 피크 전 발행",
    },
    "데이트": {
        "keywords": ["데이트", "기념일", "분위기", "와인", "오마카세"],
        "best_day": "목~금",
        "best_time": "18:00~20:00",
        "reason": "주말 데이트 계획 검색(금~토) 전 발행",
    },
    "주말": {
        "keywords": ["가족", "부모님", "모임", "단체", "파티"],
        "best_day": "수~목",
        "best_time": "20:00~21:00",
        "reason": "주말 가족 외식 검색(목~금 저녁) 전 발행",
    },
    "일반": {
        "keywords": [],
        "best_time": "10:30~11:00",
        "reason": "점심 검색 피크에 맞춰 범용 최적 시간",
    },
}

# 요일별 맛집 검색 패턴
DAY_WEIGHTS = {
    "Monday": 0.8,     # 월: 주중 시작, 검색 보통
    "Tuesday": 0.9,    # 화: 평범
    "Wednesday": 1.0,  # 수: 주중 피크 시작
    "Thursday": 1.2,   # 목: 주말 계획 검색 시작
    "Friday": 1.3,     # 금: 최고 (저녁/주말 검색 폭증)
    "Saturday": 1.1,   # 토: 실시간 검색 많음
    "Sunday": 0.7,     # 일: 가장 낮음
}


def recommend_publish_time(
    top_keywords: list[dict],
    restaurant_name: str = "",
) -> dict:
    """키워드 유형을 분석하여 최적 발행 시간을 추천한다."""
    # 키워드에서 유형 감지
    all_keywords = " ".join([kw.get("keyword", "") for kw in top_keywords])
    all_keywords_lower = all_keywords.lower()

    matched_type = "일반"
    for ptype, config in PUBLISH_WINDOWS.items():
        if ptype == "일반":
            continue
        for trigger in config.get("keywords", []):
            if trigger in all_keywords_lower or trigger in restaurant_name:
                matched_type = ptype
                break
        if matched_type != "일반":
            break

    window = PUBLISH_WINDOWS[matched_type]

    # 오늘 요일 가중치
    today = datetime.now().strftime("%A")
    day_weight = DAY_WEIGHTS.get(today, 1.0)
    day_kr = {
        "Monday": "월", "Tuesday": "화", "Wednesday": "수",
        "Thursday": "목", "Friday": "금", "Saturday": "토", "Sunday": "일",
    }.get(today, today)

    # 최적 발행 요일 추천
    best_days = sorted(DAY_WEIGHTS.items(), key=lambda x: x[1], reverse=True)[:3]
    best_days_kr = [
        {"Monday": "월", "Tuesday": "화", "Wednesday": "수",
         "Thursday": "목", "Friday": "금", "Saturday": "토", "Sunday": "일"
         }.get(d[0], d[0])
        for d in best_days
    ]

    return {
        "type": matched_type,
        "best_time": window["best_time"],
        "best_day": window.get("best_day", "목~금"),
        "reason": window["reason"],
        "today": day_kr,
        "today_score": f"{'좋음' if day_weight >= 1.0 else '보통' if day_weight >= 0.8 else '비추'}",
        "recommended_days": best_days_kr,
    }
