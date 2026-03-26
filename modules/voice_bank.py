"""
보이스 뱅크 모듈
실제 블로거 말투를 랜덤으로 조합하여 매번 다른 톤의 글을 생성한다.
매 생성마다 다른 표현 세트를 선택하여 AI 패턴 반복을 방지한다.
"""

import random


# === 문장 끝 어미 풀 (매번 다른 조합 선택) ===
ENDINGS_POOL = [
    # 세트 A: 밝고 활발한 톤
    {
        "name": "밝은톤",
        "endings": [
            "~했어요!", "~더라고요 ㅎㅎ", "~좋았어요~", "~대박이었어요",
            "~완전 추천이에요!", "~먹어봐야 해요!", "~진짜 맛있었어요~",
        ],
        "connectors": ["근데", "아 그리고", "여튼", "참고로", "ㅎㅎ 그리고"],
    },
    # 세트 B: 차분하고 담백한 톤
    {
        "name": "담백톤",
        "endings": [
            "~었어요.", "~더라고요.", "~좋았어요.", "~싶었어요.",
            "~만족이었어요.", "~괜찮았어요.", "~느낌이었어요.",
        ],
        "connectors": ["그리고", "사실", "개인적으로", "솔직히", "근데 또"],
    },
    # 세트 C: 감성적이고 수다스러운 톤
    {
        "name": "수다톤",
        "endings": [
            "~었는데요,,", "~쩔었어요 ㅋㅋ", "~미쳤어요 진짜", "~사랑이에요,,",
            "~눈물날뻔 ㅠㅠ", "~행복했답니다~", "~었거든요!",
        ],
        "connectors": ["아니 근데", "진짜", "헐 그리고", "ㅋㅋㅋ 그리고", "아 맞다"],
    },
]

# === 맛 묘사 표현 풀 (감각별로 분류) ===
TASTE_EXPRESSIONS = {
    "식감": [
        "입에서 살살 녹았어요", "씹을수록 고소함이 퍼져요",
        "바삭한 식감이 미쳤어요", "부드러움이 압권,,",
        "촉촉한 식감이 딱이었어요", "쫄깃쫄깃한 식감 최고",
        "겉바속촉 그 자체", "한입 베어무는 순간 육즙이 팡",
        "녹진한 식감에 멍때림", "탱글탱글한 식감이 좋았어요",
    ],
    "향": [
        "향이 은은하게 퍼져요~", "고소한 향이 코끝을 자극",
        "숯불 향이 살짝 배어서 더 맛있었어요",
        "불향이 장난 아니에요", "참기름 향이 확 올라와요",
        "버터 향이 슬쩍 나서 고급진 느낌", "마늘 향이 식욕 자극 200%",
    ],
    "온도": [
        "뜨끈한 게 속이 확 풀려요", "차갑게 먹으니까 더 시원하고 좋았어요",
        "따끈따끈한 상태로 나와서 바로 먹었어요",
        "살짝 미지근해진 것도 맛있었어요 ㅋㅋ",
        "입안에서 뜨끈한 국물이 확 퍼져요",
    ],
    "비주얼": [
        "비주얼 실화?!", "나오자마자 사진부터 찍었어요 ㅋㅋ",
        "색감이 너무 예뻤어요~", "인스타 각이었어요,,",
        "접시 위에 작품이 올라온 느낌", "비주얼만으로 이미 합격",
        "나오는 순간 우와 소리가 절로", "사진보다 실물이 더 예뻐요",
    ],
    "간": [
        "간이 딱 적당했어요", "살짝 짜서 밥이랑 먹으면 딱이에요",
        "간이 세지 않아서 계속 먹게 돼요",
        "양념이 과하지 않고 재료 맛이 살아있었어요",
        "소스가 은근 중독성 있어요", "살짝 달큰한 양념이 포인트",
    ],
}

# === 에피소드 패턴 (동행인 반응 등) ===
COMPANION_REACTIONS = [
    '{companion}이/가 "{food}" 먹자마자 눈이 커지면서 "이거 미쳤다" 하더라고요 ㅋㅋ',
    '{companion}이/가 젓가락을 멈출 수가 없다면서 혼자 거의 다 먹었어요 ㅋㅋ',
    '{companion}이/가 "여기 단골 해야 된다" 이러면서 벌써 다음 약속 잡자고 했어요',
    '{companion}이/가 먹다가 갑자기 조용해져서 봤더니 집중하고 있었어요 ㅋㅋㅋ',
    '{companion}이/가 "이 가격에 이 맛이면 완전 가성비다" 라고 하더라고요~',
    '{companion}이/가 사진 찍는 거 잊어버리고 먹기 바빴어요 ㅋㅋ',
    '{companion}한테 여기 데려왔는데 반응이 완전 폭발이었어요 ㅎㅎ',
    '{companion}이/가 다 먹고 나서 "오늘 잘 왔다" 이러는 거 보고 뿌듯했어요~',
]

# === 전환 표현 (섹션 간 자연스러운 연결) ===
TRANSITIONS = {
    "to_interior": [
        "안으로 들어가볼게요~",
        "내부는 이런 느낌이에요!",
        "자리 안내받고 둘러봤는데요,",
        "들어가자마자 느낌이 좋았어요",
    ],
    "to_menu": [
        "메뉴판 한번 볼게요~",
        "자리 앉자마자 메뉴판 펼쳤어요 ㅎㅎ",
        "뭘 먹을지 고민하다가~",
        "이날 저희가 주문한 건!",
    ],
    "to_food": [
        "드디어 음식이 나왔어요!",
        "기다리던 메뉴 등장~",
        "주문하고 얼마 안 돼서 나왔어요!",
        "오래 기다릴 필요 없이 금방 나왔어요~",
    ],
    "to_review": [
        "맛은요~",
        "한입 먹어봤는데요,",
        "먹어본 솔직 후기 갑니다",
        "자 그럼 본격적으로 리뷰 시작할게요!",
    ],
    "to_closing": [
        "정리하자면요~",
        "이날 다녀온 솔직 총평!",
        "마지막으로 한줄 정리하면",
        "결론부터 말하면요,",
    ],
}

# === 도입부 패턴 (매번 다른 시작) ===
OPENING_PATTERNS = [
    # 패턴 1: 인사 + 방문 계기
    "안녕하세요~\n오늘은 {region}에 있는 {name} 다녀온 후기에요!\n{reason}",
    # 패턴 2: 바로 시작
    "{region} {category} 찾다가 발견한 {name}!\n{reason}",
    # 패턴 3: 결론 먼저
    "결론부터 말하면 재방문 의사 {revisit_pct}%인 곳이에요 ㅎㅎ\n{region}에 있는 {name} 다녀왔어요~\n{reason}",
    # 패턴 4: 에피소드 시작
    "{reason}\n그래서 찾아간 곳이 {region} {name}이에요!",
    # 패턴 5: 질문형
    "{region}에서 {category} 어디 가세요?!\n저는 이번에 {name} 다녀왔는데 완전 대만족이었어요~",
    # 패턴 6: 추천형
    "{region} {category} 고민이시라면 여기 추천드려요!\n{name} 다녀온 솔직 후기에요~",
]

# === 방문 이유 풀 ===
VISIT_REASONS = [
    "친구가 여기 진짜 맛있다고 해서 바로 예약했어요",
    "인스타에서 계속 보여서 궁금했던 곳이에요",
    "네이버 검색하다가 후기가 좋아서 가봤어요",
    "지나가다 줄 서있길래 궁금해서 방문했어요",
    "블로그에서 리뷰 보고 바로 예약했어요 ㅎㅎ",
    "여기 소문 듣고 일부러 찾아갔어요~",
    "예전부터 가보고 싶었는데 드디어 갔어요!",
    "동네 사람들 사이에서 유명한 곳이라고 해서요~",
]

# === 아쉬운 점 풀 (신뢰감 확보용) ===
MINOR_COMPLAINTS = [
    "한 가지 아쉬운 건 웨이팅이 좀 있었어요",
    "주차가 좀 불편한 게 아쉬웠어요",
    "양이 살짝 아쉬울 수 있는데 맛으로 커버돼요",
    "가격이 좀 있는 편이긴 해요",
    "좌석 간격이 좀 좁았어요",
    "반찬 리필이 좀 느렸어요",
    "메뉴가 많아서 고르기 어려웠어요 ㅋㅋ 행복한 고민",
]

# === 마무리 표현 풀 ===
CLOSING_PATTERNS = [
    "이상 {name} 내돈내산 솔직후기였습니다!\n다음에 또 맛있는 곳 다녀오면 후기 올릴게요~",
    "{region} {category} 고민이시면 {name} 한번 가보세요!\n후회 안 하실 거예요~ ㅎㅎ",
    "오늘도 맛있는 하루였어요~\n{name} 재방문 의사 100%입니다!",
    "{name} 솔직 후기 끝!\n여기 진짜 또 갈 거예요~ 다음엔 {next_menu} 먹어볼 예정이에요 ㅎㅎ",
]


def pick_voice_set() -> dict:
    """이번 생성에 사용할 보이스 세트를 랜덤으로 선택한다."""
    tone = random.choice(ENDINGS_POOL)
    return {
        "tone_name": tone["name"],
        "endings": tone["endings"],
        "connectors": tone["connectors"],
        "taste_senses": random.sample(list(TASTE_EXPRESSIONS.keys()), k=min(3, len(TASTE_EXPRESSIONS))),
        "opening_pattern": random.choice(OPENING_PATTERNS),
        "visit_reason": random.choice(VISIT_REASONS),
        "minor_complaint": random.choice(MINOR_COMPLAINTS),
        "closing_pattern": random.choice(CLOSING_PATTERNS),
    }


def build_voice_guide(voice: dict) -> str:
    """선택된 보이스 세트를 프롬프트용 가이드로 변환한다."""
    endings_text = ", ".join(voice["endings"][:5])
    connectors_text = ", ".join(voice["connectors"])

    # 감각별 표현 3~4개씩 뽑기
    taste_examples = []
    for sense in voice["taste_senses"]:
        exprs = random.sample(TASTE_EXPRESSIONS[sense], k=min(3, len(TASTE_EXPRESSIONS[sense])))
        taste_examples.append(f"  {sense}: {' / '.join(exprs)}")
    taste_text = "\n".join(taste_examples)

    return f"""이번 글의 톤: {voice["tone_name"]}

문장 끝 패턴 (이 중에서 골라서 사용, 같은 어미 연속 사용 금지):
{endings_text}

문장 연결 (자연스럽게 사용):
{connectors_text}

메뉴 묘사 시 이런 감각 표현 활용:
{taste_text}
"""


def build_companion_reaction(companion: str, food: str) -> str:
    """동행인 반응 문장을 생성한다."""
    if not companion:
        return ""
    template = random.choice(COMPANION_REACTIONS)
    return template.format(companion=companion, food=food)


def get_random_transitions() -> dict:
    """섹션 전환 표현을 랜덤으로 하나씩 선택한다."""
    return {key: random.choice(values) for key, values in TRANSITIONS.items()}
