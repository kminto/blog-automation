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

    # 7) 문장 시작 패턴 (첫 2~3글자)
    start_counter = Counter()
    for s in sentences:
        if len(s) >= 4:
            # 구어체 시작 패턴 추출
            for starter in ["근데", "사실", "아무래도", "여튼", "참고로",
                            "개인적으로", "솔직히", "저희는", "저는", "이건",
                            "그래서", "확실히", "드디어", "아 그리고"]:
                if s.startswith(starter):
                    start_counter[starter] += 1

    # 8) 사진 설명 말투 추출
    photo_descriptions = re.findall(
        r'\[사진[:\s]*([^\]]+)\]', all_text,
    )
    # 움짤 설명도
    gif_descriptions = re.findall(
        r'\[움짤[:\s]*([^\]]+)\]', all_text,
    )

    # 9) 섹션별 문장 분류
    section_sentences = {
        "도입부": [],  # 글 시작 3~5줄
        "메뉴리뷰": [],  # 메뉴명 뒤 감상
        "총평": [],  # 마무리
    }
    for sample in samples:
        lines = [l.strip() for l in sample["text"].split("\n") if l.strip()]
        # 도입부 (첫 5줄)
        for line in lines[:5]:
            if len(line) > 5 and not line.startswith("#") and not line.startswith("["):
                section_sentences["도입부"].append(line)
        # 마무리 (끝 5줄)
        for line in lines[-5:]:
            if len(line) > 5 and not line.startswith("#"):
                section_sentences["총평"].append(line)
        # 메뉴 리뷰 (메뉴 소제목 뒤 3줄)
        for i, line in enumerate(lines):
            if "🍽" in line or "🍺" in line or "메인" in line:
                for j in range(i + 1, min(i + 4, len(lines))):
                    if len(lines[j]) > 5 and not lines[j].startswith("["):
                        section_sentences["메뉴리뷰"].append(lines[j])

    # 10) 자주 쓰는 문장 틀 (빈칸 패턴)
    sentence_templates = []
    template_patterns = [
        (r'저희는 .+했는데요', "저희는 ~했는데요"),
        (r'개인적으로 .+같아요', "개인적으로 ~같아요"),
        (r'.+추천드려요', "~추천드려요"),
        (r'.+먹어봐야 .+', "~먹어봐야 ~"),
        (r'다음에.+먹어볼', "다음에 ~먹어볼"),
        (r'.+하기 좋은', "~하기 좋은"),
        (r'솔직히 .+', "솔직히 ~"),
        (r'.+느낌이었어요', "~느낌이었어요"),
    ]
    for pattern, label in template_patterns:
        count = len(re.findall(pattern, all_text))
        if count > 0:
            sentence_templates.append({"pattern": label, "count": count})

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
        "sentence_starters": start_counter.most_common(10),
        "photo_descriptions": photo_descriptions[:15],
        "gif_descriptions": gif_descriptions[:5],
        "section_samples": {
            "도입부": section_sentences["도입부"][:10],
            "메뉴리뷰": section_sentences["메뉴리뷰"][:10],
            "총평": section_sentences["총평"][:10],
        },
        "sentence_templates": sorted(sentence_templates, key=lambda x: x["count"], reverse=True)[:8],
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

    # 어미 패턴 (비율로 표현)
    endings = profile.get("top_endings", [])[:8]
    total_endings = sum(e[1] for e in endings) or 1
    endings_lines = []
    for e in endings:
        pct = round(e[1] / total_endings * 100)
        endings_lines.append(f"  {e[0]} ({pct}%) — 가장 {'자주' if pct > 15 else '가끔'} 사용")
    endings_text = "\n".join(endings_lines)

    # 감탄사 (사용 빈도로 가이드)
    expressions = profile.get("top_expressions", [])[:6]
    expr_lines = []
    for e in expressions:
        freq = "매우 자주" if e[1] > 100 else "자주" if e[1] > 30 else "가끔"
        expr_lines.append(f"  {e[0]} — {freq} ({e[1]}회)")
    expr_text = "\n".join(expr_lines)

    # 구어체
    colloquials = [e[0] for e in profile.get("top_colloquials", [])[:10]]
    colloq_text = ", ".join(colloquials)

    # 이모지
    emojis = profile.get("top_emojis", [])[:8]
    emoji_text = ", ".join([f"{e[0]}({e[1]})" for e in emojis])

    # 문장 스타일
    stats = profile.get("sentence_stats", {})

    # 문장 시작 패턴
    starters = profile.get("sentence_starters", [])[:8]
    starter_text = ", ".join([f'"{s[0]}"({s[1]})' for s in starters]) if starters else "없음"

    # 사진 설명 말투
    photos = profile.get("photo_descriptions", [])[:8]
    photo_text = "\n".join([f'  [사진: {p}]' for p in photos]) if photos else "  (사진 설명 데이터 없음)"

    # 섹션별 실제 문장
    sections = profile.get("section_samples", {})
    intro_samples = sections.get("도입부", [])[:5]
    review_samples = sections.get("메뉴리뷰", [])[:5]
    closing_samples = sections.get("총평", [])[:5]

    intro_text = "\n".join([f'  "{s}"' for s in intro_samples]) if intro_samples else "  (없음)"
    review_text = "\n".join([f'  "{s}"' for s in review_samples]) if review_samples else "  (없음)"
    closing_text = "\n".join([f'  "{s}"' for s in closing_samples]) if closing_samples else "  (없음)"

    # 문장 틀
    templates = profile.get("sentence_templates", [])[:6]
    template_text = ", ".join([f'"{t["pattern"]}"({t["count"]})' for t in templates]) if templates else "없음"

    # 특색 문장
    samples = profile.get("sample_sentences", [])[:15]
    sample_text = "\n".join([f'  - "{s}"' for s in samples])

    return f"""[내 블로그 말투 완전 분석 - {profile.get('sample_count', 0)}편 / {profile.get('total_chars', 0):,}자 기반]

1. 문장 끝 어미 (이 비율대로 사용할 것):
{endings_text}

2. 감탄사/특수문자 (이 빈도를 따를 것):
{expr_text}

3. 자주 쓰는 구어체: {colloq_text}

4. 문장 시작 패턴: {starter_text}

5. 자주 쓰는 문장 틀: {template_text}

6. 문장 스타일:
  평균 {stats.get('avg_length', 0)}자 / 짧은 문장 {stats.get('short_ratio', 0)}% / 긴 문장 {stats.get('long_ratio', 0)}%
  → 1~2줄 단문 위주, 3줄 이상 이어지면 안 됨

7. 이모지: {emoji_text}

8. 사진 설명 말투 (이렇게 쓸 것):
{photo_text}

9. 도입부에서 자주 쓰는 말:
{intro_text}

10. 메뉴 리뷰에서 자주 쓰는 말:
{review_text}

11. 총평/마무리에서 자주 쓰는 말:
{closing_text}

12. 내가 실제로 쓴 특색 문장 (이 톤을 복제할 것):
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
