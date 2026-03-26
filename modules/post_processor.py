"""
AI 냄새 후처리 모듈
생성된 블로그 글에서 AI 특유의 패턴을 탐지하고 자동 교정한다.
"""

import re
import random


# === AI 특유 표현 → 자연스러운 대체어 ===
AI_REPLACEMENTS = {
    # 격식체 → 구어체
    "합니다": "해요",
    "됩니다": "돼요",
    "있습니다": "있어요",
    "없습니다": "없어요",
    "입니다": "이에요",
    "것 같습니다": "거 같아요",
    "드립니다": "드려요",
    "않습니다": "않아요",
    # AI 과장 표현 → 자연스러운 표현
    "맛의 하모니": "맛 조합",
    "미각의 향연": "진짜 맛있었어요",
    "입안 가득 퍼지는": "입안에 퍼지는",
    "풍미가 가득한": "맛있는",
    "완벽한 조화": "찰떡 조합",
    "특별한 경험": "좋은 경험",
    "잊을 수 없는": "기억에 남는",
    "압도적인": "진짜 대단한",
    "환상적인": "진짜 좋은",
    "독보적인": "독특한",
    # 접속부사 과용
    "또한": "그리고",
    "뿐만 아니라": "게다가",
    "그러므로": "그래서",
    "따라서": "그래서",
    "한편": "",
    "더불어": "그리고",
}

# === 반복 사용 금지 표현 (3회 이상이면 대체) ===
OVERUSED_WORDS = {
    "다양한": ["여러 가지", "이것저것", "가지각색의", ""],
    "풍부한": ["넉넉한", "푸짐한", "듬뿍"],
    "특별한": ["색다른", "남다른", "독특한"],
    "정말": ["진짜", "솔직히", "ㅎㅎ"],
    "매우": ["엄청", "완전", "진짜"],
    "맛있었어요": [
        "맛 좋았어요", "괜찮았어요", "만족이었어요",
        "입에 딱 맞았어요", "최고였어요",
    ],
    "좋았어요": [
        "괜찮았어요", "만족이었어요", "마음에 들었어요", "딱이었어요",
    ],
}

# === 마크다운 잔재 정리 패턴 ===
MARKDOWN_PATTERNS = [
    (r'\*\*(.+?)\*\*', r'\1'),  # **굵은글씨** → 일반
    (r'#{1,3}\s*', ''),          # ## 제목 → 제거 (출력 형식 헤더 제외)
    (r'^---+\s*$', '', re.MULTILINE),  # --- 구분선
    (r'^\*\s+', '', re.MULTILINE),     # * 목록
    (r'^-\s+', '', re.MULTILINE),      # - 목록
]


def _fix_formal_endings(text: str) -> str:
    """격식체를 구어체로 교정한다."""
    for formal, casual in AI_REPLACEMENTS.items():
        text = text.replace(formal, casual)
    return text


def _fix_overused_words(text: str) -> str:
    """과다 사용된 표현을 다양하게 교체한다."""
    for word, alternatives in OVERUSED_WORDS.items():
        count = text.count(word)
        if count <= 2:
            continue

        # 처음 2번은 유지, 3번째부터 교체
        parts = text.split(word)
        result = []
        for i, part in enumerate(parts):
            result.append(part)
            if i < len(parts) - 1:
                if i < 2:
                    result.append(word)
                else:
                    replacement = random.choice(alternatives) if alternatives else ""
                    result.append(replacement)
        text = "".join(result)

    return text


def _fix_markdown_remnants(text: str) -> str:
    """마크다운 잔재를 정리한다. 단 출력 형식 헤더(### 제목 후보 등)는 유지."""
    lines = text.split("\n")
    result = []
    for line in lines:
        # 출력 형식 헤더는 유지
        if line.strip().startswith("### 제목 후보") or \
           line.strip().startswith("### 본문") or \
           line.strip().startswith("### 해시태그"):
            result.append(line)
            continue

        # **굵은글씨** 제거
        line = re.sub(r'\*\*(.+?)\*\*', r'\1', line)
        # --- 구분선 제거
        if re.match(r'^---+\s*$', line):
            continue
        # 목록 기호 제거 (사진/움짤/출처입력 설명은 유지)
        s = line.strip()
        if not s.startswith("[사진") and not s.startswith("[움짤") \
                and s != "출처 입력" and s != "사진 설명을 입력하세요.":
            line = re.sub(r'^[\*\-]\s+', '', line)
        result.append(line)

    return "\n".join(result)


def _fix_long_paragraphs(text: str) -> str:
    """4줄 이상 연속된 문단을 줄바꿈으로 분리한다."""
    lines = text.split("\n")
    result = []
    consecutive = 0

    for line in lines:
        stripped = line.strip()
        if stripped == "":
            consecutive = 0
            result.append(line)
        elif stripped.startswith("[사진") or stripped.startswith("[움짤") or \
             stripped.startswith("[운영정보") or stripped.startswith("위치 :") or \
             stripped == "출처 입력" or stripped == "사진 설명을 입력하세요.":
            consecutive = 0
            result.append(line)
        else:
            consecutive += 1
            result.append(line)
            if consecutive >= 3:
                result.append("")
                consecutive = 0

    return "\n".join(result)


def _fix_repetitive_sentence_starts(text: str) -> str:
    """연속 3문장 이상 같은 단어로 시작하면 변주한다."""
    lines = text.split("\n")
    if len(lines) < 3:
        return text

    result = [lines[0]]
    for i in range(1, len(lines)):
        current = lines[i].strip()
        prev = lines[i - 1].strip()

        if not current or not prev:
            result.append(lines[i])
            continue

        # 같은 단어로 시작하는지 확인
        curr_start = current[:2] if len(current) >= 2 else current
        prev_start = prev[:2] if len(prev) >= 2 else prev

        if i >= 2:
            prev2 = lines[i - 2].strip()
            prev2_start = prev2[:2] if len(prev2) >= 2 else prev2
            if curr_start == prev_start == prev2_start and curr_start:
                # 앞에 전환어 추가
                fillers = ["ㅎㅎ ", "근데 ", "아 ", "여튼 ", "참고로 "]
                lines[i] = random.choice(fillers) + current

        result.append(lines[i])

    return "\n".join(result)


def process_blog_text(text: str) -> str:
    """생성된 블로그 글을 후처리한다."""
    text = _fix_formal_endings(text)
    text = _fix_overused_words(text)
    text = _fix_markdown_remnants(text)
    text = _fix_long_paragraphs(text)
    text = _fix_repetitive_sentence_starts(text)
    return text


def get_ai_score(text: str) -> dict:
    """AI 냄새 점수를 측정한다 (디버그용). 낮을수록 좋음."""
    issues = []

    # 격식체 검사
    formal_count = sum(1 for word in AI_REPLACEMENTS if word in text)
    if formal_count > 0:
        issues.append(f"격식체 {formal_count}개")

    # 과장 표현 검사
    exaggerations = ["맛의 하모니", "미각의 향연", "완벽한 조화", "환상적인"]
    exag_count = sum(1 for e in exaggerations if e in text)
    if exag_count > 0:
        issues.append(f"과장 표현 {exag_count}개")

    # 반복 표현 검사
    for word in ["맛있었어요", "좋았어요", "다양한", "풍부한"]:
        count = text.count(word)
        if count >= 3:
            issues.append(f"'{word}' {count}회 반복")

    # 긴 문단 검사
    paragraphs = text.split("\n\n")
    long_paras = sum(1 for p in paragraphs if p.count("\n") >= 4)
    if long_paras > 0:
        issues.append(f"긴 문단 {long_paras}개")

    # 마크다운 잔재
    md_count = len(re.findall(r'\*\*|^#{1,3}\s|^---', text, re.MULTILINE))
    if md_count > 0:
        issues.append(f"마크다운 잔재 {md_count}개")

    score = formal_count * 3 + exag_count * 5 + long_paras * 2 + md_count * 2
    return {
        "score": score,
        "grade": "좋음" if score <= 5 else "보통" if score <= 15 else "개선필요",
        "issues": issues,
    }
