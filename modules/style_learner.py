"""
블로그 말투 학습 모듈
실제 블로그 글을 크롤링하여 말투 패턴을 자동 분석하고,
프롬프트에 활용할 스타일 프로필을 생성한다.
"""

import json
import os
import re
import time
from collections import Counter
from html import unescape
from urllib.parse import unquote

import requests

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SAMPLES_FILE = os.path.join(DATA_DIR, "my_blog_samples.json")
STYLE_PROFILE_FILE = os.path.join(DATA_DIR, "my_style_profile.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36"
    ),
}


def _fetch_post_list(blog_id: str, max_pages: int = 5) -> list[dict]:
    """블로그에서 맛집 글 목록을 가져온다."""
    food_keywords = [
        "맛집", "후기", "치킨", "오마카세", "양꼬치", "국밥", "고기",
        "카페", "브런치", "모임", "데이트", "점심", "솔직", "내돈내산",
        "메뉴", "훠궈", "삼겹살", "술집", "리뷰", "추천",
    ]

    all_posts = []
    for page in range(1, max_pages + 1):
        url = (
            f"https://blog.naver.com/PostTitleListAsync.naver"
            f"?blogId={blog_id}&currentPage={page}&countPerPage=10"
        )
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            data = json.loads(r.text.replace("'", '"'))
            posts = data.get("postList", [])
            if not posts:
                break
            for p in posts:
                title = unquote(p.get("title", "").replace("+", " "))
                if any(kw in title for kw in food_keywords):
                    all_posts.append({"logNo": p["logNo"], "title": title})
        except Exception:
            break
        if page > 1:
            time.sleep(0.5)

    return all_posts


def _fetch_post_text(blog_id: str, log_no: str) -> str:
    """단일 글의 본문 텍스트를 추출한다."""
    url = f"https://m.blog.naver.com/{blog_id}/{log_no}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        # se-text-paragraph에서 텍스트 추출
        paragraphs = re.findall(
            r'<p class="se-text-paragraph[^"]*"[^>]*>(.*?)</p>',
            r.text, re.DOTALL,
        )
        lines = []
        for p in paragraphs:
            cleaned = re.sub(r'<[^>]+>', '', p).strip()
            cleaned = unescape(cleaned)
            # 빈 줄, 공백만 있는 줄 건너뛰기
            if cleaned and cleaned != "\u200b":
                lines.append(cleaned)
        return "\n".join(lines)
    except Exception:
        return ""


def crawl_my_blog(blog_id: str = "rinx_x", max_posts: int = 8) -> list[dict]:
    """블로그 맛집 글을 크롤링하여 저장한다."""
    posts = _fetch_post_list(blog_id)
    collected = []

    for post in posts[:max_posts]:
        text = _fetch_post_text(blog_id, post["logNo"])
        if len(text) > 300:
            collected.append({
                "title": post["title"],
                "logNo": post["logNo"],
                "text": text,
                "length": len(text),
            })
        time.sleep(0.5)

    # 저장
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SAMPLES_FILE, "w", encoding="utf-8") as f:
        json.dump(collected, f, ensure_ascii=False, indent=2)

    return collected


def analyze_style(samples: list[dict] = None) -> dict:
    """수집된 글에서 말투 패턴을 분석한다."""
    if samples is None:
        if not os.path.exists(SAMPLES_FILE):
            return {"error": "블로그 샘플이 없습니다. 먼저 크롤링해주세요."}
        with open(SAMPLES_FILE, "r", encoding="utf-8") as f:
            samples = json.load(f)

    if not samples:
        return {"error": "분석할 글이 없습니다."}

    all_text = "\n".join([s["text"] for s in samples])
    sentences = [s.strip() for s in re.split(r'[.!?\n]', all_text) if s.strip()]

    # 1) 문장 끝 어미 분석
    ending_counter = Counter()
    ending_patterns = [
        ("~했어요", r'했어요'),
        ("~었어요", r'었어요'),
        ("~더라고요", r'더라고요'),
        ("~좋았어요", r'좋았어요'),
        ("~거든요", r'거든요'),
        ("~싶었어요", r'싶었어요'),
        ("~있어요", r'있어요'),
        ("~없어요", r'없어요'),
        ("~했답니다", r'했답니다'),
        ("~추천드려요", r'추천드려요'),
        ("~드릴게요", r'드릴게요'),
        ("~인데요", r'인데요'),
        ("~해요", r'해요'),
        ("~이에요", r'이에요'),
        ("~예요", r'예요'),
        ("~같아요", r'같아요'),
    ]
    for label, pattern in ending_patterns:
        count = len(re.findall(pattern, all_text))
        if count > 0:
            ending_counter[label] = count

    # 2) 감탄사/특수 표현 분석
    expression_counter = Counter()
    expressions = {
        "ㅎㅎ": r'ㅎㅎ',
        "ㅋㅋ": r'ㅋㅋ',
        ",,": r',,',
        "~": r'~',
        "…": r'…',
        "!!": r'!!',
        "ㅠㅠ": r'ㅠㅠ',
        "?!": r'\?!',
    }
    for label, pattern in expressions.items():
        count = len(re.findall(pattern, all_text))
        if count > 0:
            expression_counter[label] = count

    # 3) 자주 쓰는 구어체 표현
    colloquial_counter = Counter()
    colloquials = [
        "여튼", "진짜", "근데", "솔직히", "개인적으로", "완전",
        "딱", "엄청", "되게", "약간", "후후", "드디어", "역시",
        "아무래도", "확실히", "사실", "참고로", "내돈내산",
    ]
    for word in colloquials:
        count = all_text.count(word)
        if count > 0:
            colloquial_counter[word] = count

    # 4) 문장 길이 분포
    lengths = [len(s) for s in sentences if len(s) > 2]
    avg_len = sum(lengths) / len(lengths) if lengths else 0
    short_ratio = sum(1 for l in lengths if l <= 15) / len(lengths) if lengths else 0
    long_ratio = sum(1 for l in lengths if l >= 40) / len(lengths) if lengths else 0

    # 5) 실제 예시 문장 추출 (특색 있는 문장들)
    interesting_sentences = []
    for s in sentences:
        # ㅎㅎ, ,,, ~, ㅋㅋ 등이 포함된 자연스러운 문장
        if any(marker in s for marker in ["ㅎㅎ", ",,", "ㅋㅋ", "~"]):
            if 10 < len(s) < 60:
                interesting_sentences.append(s)

    # 6) 자주 쓰는 이모지
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0\U0001f900-\U0001f9FF"
        "\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF]+",
        flags=re.UNICODE,
    )
    emoji_counter = Counter()
    for match in emoji_pattern.finditer(all_text):
        for char in match.group():
            emoji_counter[char] += 1

    profile = {
        "blog_id": samples[0].get("logNo", "unknown") if samples else "unknown",
        "sample_count": len(samples),
        "total_chars": len(all_text),
        "top_endings": ending_counter.most_common(8),
        "top_expressions": expression_counter.most_common(8),
        "top_colloquials": colloquial_counter.most_common(10),
        "top_emojis": emoji_counter.most_common(10),
        "sentence_stats": {
            "avg_length": round(avg_len, 1),
            "short_ratio": round(short_ratio * 100, 1),
            "long_ratio": round(long_ratio * 100, 1),
        },
        "sample_sentences": interesting_sentences[:20],
    }

    # 프로필 저장
    with open(STYLE_PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    return profile


def get_style_profile() -> dict:
    """저장된 스타일 프로필을 로드한다."""
    if not os.path.exists(STYLE_PROFILE_FILE):
        return None
    with open(STYLE_PROFILE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_style_prompt_from_profile(profile: dict) -> str:
    """스타일 프로필을 프롬프트용 텍스트로 변환한다."""
    if not profile or "error" in profile:
        return ""

    # 어미 패턴
    endings = [f"{e[0]}({e[1]}회)" for e in profile.get("top_endings", [])[:6]]
    endings_text = ", ".join(endings)

    # 감탄사
    expressions = [f"{e[0]}({e[1]}회)" for e in profile.get("top_expressions", [])[:6]]
    expr_text = ", ".join(expressions)

    # 구어체
    colloquials = [e[0] for e in profile.get("top_colloquials", [])[:8]]
    colloq_text = ", ".join(colloquials)

    # 이모지
    emojis = [e[0] for e in profile.get("top_emojis", [])[:8]]
    emoji_text = " ".join(emojis)

    # 문장 길이
    stats = profile.get("sentence_stats", {})

    # 특색 있는 문장 샘플
    samples = profile.get("sample_sentences", [])[:10]
    sample_text = "\n".join([f'  - "{s}"' for s in samples])

    return f"""[내 블로그 말투 분석 결과 - 이 패턴을 그대로 따라할 것]

자주 쓰는 문장 끝: {endings_text}
자주 쓰는 감탄사: {expr_text}
자주 쓰는 구어체: {colloq_text}
자주 쓰는 이모지: {emoji_text}
문장 평균 길이: {stats.get('avg_length', 0)}자 (짧은 문장 {stats.get('short_ratio', 0)}%, 긴 문장 {stats.get('long_ratio', 0)}%)

내가 실제로 쓴 문장들 (이 톤을 그대로 유지):
{sample_text}
"""


def get_best_example_posts(count: int = 2) -> list[str]:
    """저장된 샘플 중 가장 좋은 예시 글을 반환한다."""
    if not os.path.exists(SAMPLES_FILE):
        return []

    with open(SAMPLES_FILE, "r", encoding="utf-8") as f:
        samples = json.load(f)

    if not samples:
        return []

    # 길이가 적당한 글 (1000~4000자) 우선
    good_samples = sorted(
        [s for s in samples if 1000 <= s["length"] <= 4000],
        key=lambda x: x["length"],
        reverse=True,
    )

    # 부족하면 전체에서
    if len(good_samples) < count:
        good_samples = sorted(samples, key=lambda x: x["length"], reverse=True)

    return [s["text"] for s in good_samples[:count]]
