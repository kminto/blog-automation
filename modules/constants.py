"""
상수 정의 모듈
키워드 점수 계산, 경쟁도 가중치, 트렌드 가중치 등 시스템 전역 상수를 관리한다.
"""

# === 경쟁도(compIdx) 가중치 (차이를 크게 벌려서 낮은 경쟁도 키워드가 유리하도록) ===
COMPETITION_WEIGHTS = {
    "낮음": 0.5,
    "중간": 1.0,
    "높음": 2.0,
}

# === 트렌드 가중치 ===
TREND_WEIGHTS = {
    "상승": 1.5,   # 최근 검색량 증가 키워드 가산
    "유지": 1.0,   # 변동 없음
    "하락": 0.6,   # 검색량 감소 키워드 페널티
}

# === 키워드 점수 공식 ===
# final_score = (search_volume * trend_weight) / competition_weight
# 경쟁도 낮음(0.5)은 높음(2.0)보다 4배 유리 → 롱테일 키워드 부각
# search_volume = monthlyPcQcCnt + monthlyMobileQcCnt

# === 키워드 조합 제한 ===
MAX_KEYWORD_COMBINATIONS = 50  # API에 보낼 최대 키워드 조합 수
TOP_KEYWORDS_FOR_CONTENT = 10  # 본문 생성에 사용할 상위 키워드 수

# === 상황 키워드 ===
SITUATION_KEYWORDS = [
    "맛집", "데이트", "가족모임", "회식", "술집",
    "혼밥", "점심", "저녁", "브런치", "카페",
]

# === OpenAI API 설정 ===
OPENAI_MODEL = "gpt-4o"
OPENAI_MAX_TOKENS = 8192

# === 데이터랩 API 설정 ===
DATALAB_TIME_UNIT = "week"
DATALAB_PERIOD_MONTHS = 3  # 최근 3개월 트렌드 분석

# === 블로그 생성 설정 ===
TITLE_COUNT = 5          # 제목 후보 수
HASHTAG_MIN = 18         # 최소 해시태그 수
HASHTAG_MAX = 22         # 최대 해시태그 수
