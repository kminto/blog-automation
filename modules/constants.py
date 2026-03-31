"""
상수 정의 모듈
2026년 네이버 C-Rank/D.I.A+ 알고리즘 기반 SEO 최적화 상수.
"""

# === 경쟁도(compIdx) 가중치 ===
# 롱테일 키워드 극대화: 낮은 경쟁도에 6배 유리하게 설정
COMPETITION_WEIGHTS = {
    "낮음": 0.3,   # 롱테일 키워드 최우선 (기존 0.5 → 0.3)
    "중간": 1.0,
    "높음": 2.5,   # 경쟁 치열한 키워드 더 강한 페널티 (기존 2.0 → 2.5)
}

# === 트렌드 가중치 ===
TREND_WEIGHTS = {
    "상승": 1.8,   # 상승 트렌드 더 크게 가산 (기존 1.5 → 1.8)
    "유지": 1.0,
    "하락": 0.4,   # 하락 트렌드 더 강한 페널티 (기존 0.6 → 0.4)
}

# === 키워드 점수 공식 (D.I.A+ 반영) ===
# final_score = (search_volume * trend_weight * longtail_bonus) / competition_weight
# 롱테일 보너스: 3~5단어 키워드에 가산점
# 최소 유의미 검색량: 월 30회 (30 미만은 유입 기대 어려움)
MIN_SEARCH_VOLUME = 30  # 최소 유의미 검색량 (기존 100 → 30)
LONGTAIL_BONUS = 1.3     # 3단어 이상 롱테일 키워드 가산

# === 키워드 조합 제한 ===
MAX_KEYWORD_COMBINATIONS = 50
TOP_KEYWORDS_FOR_CONTENT = 10

# === 상황 키워드 ===
SITUATION_KEYWORDS = [
    "맛집", "맛집추천", "점심", "저녁", "회식",
    "가족모임", "데이트", "혼밥", "브런치", "카페", "술집",
]

# === OpenAI API 설정 ===
OPENAI_MODEL = "gpt-4o"
OPENAI_MAX_TOKENS = 8192

# === 데이터랩 API 설정 ===
DATALAB_TIME_UNIT = "week"
DATALAB_PERIOD_MONTHS = 3

# === 블로그 생성 설정 (2026 SEO 기준) ===
TITLE_COUNT = 5
TITLE_MIN_LENGTH = 20    # 제목 최소 길이 (기존 25 → 20)
TITLE_MAX_LENGTH = 25    # 제목 최대 길이 (기존 40 → 25, 모바일 잘림 방지)
HASHTAG_MIN = 15         # 최소 해시태그
HASHTAG_MAX = 20         # 최대 해시태그
PHOTO_MIN = 5            # 최소 사진 수 (기존 12 → 5)
PHOTO_MAX = 10           # 최대 사진 수 (다양한 앵글, 과다 금지)

# === 키워드 밀도 (D.I.A+ 기준) ===
KEYWORD_DENSITY_TARGET = 0.015  # 본문 대비 1.5% (과하면 스팸 판정)
KEYWORD_MAX_REPEAT = 5          # 동일 키워드 최대 반복 횟수
