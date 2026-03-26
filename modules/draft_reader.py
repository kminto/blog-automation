"""
네이버 블로그 글 사진 추출 모듈
발행된 글(비공개 포함)에서 사진을 순서대로 추출하고 다운로드한다.
사용자가 사진만 올린 글 → 사진 추출 → AI 분석 → 본문 자동 생성.
"""

import re

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36"
    ),
}


def extract_photos_from_post(blog_id: str, log_no: str) -> list[dict]:
    """발행된 블로그 글에서 사진을 순서대로 추출하고 다운로드한다.

    Args:
        blog_id: 블로그 ID (예: "rinx_x")
        log_no: 글 번호 (예: "224115890458")

    Returns:
        [{"index": 0, "url": "https://...", "bytes": b"...", "name": "photo_0.jpg"}, ...]
    """
    url = f"https://m.blog.naver.com/{blog_id}/{log_no}"
    r = requests.get(url, headers=HEADERS, timeout=15)

    if r.status_code != 200:
        raise RuntimeError(f"글을 가져올 수 없습니다. (상태: {r.status_code})")

    # se-module-image 블록에서 순서대로 이미지 추출
    img_blocks = re.findall(
        r'class="se-module se-module-image".*?</div>\s*</div>\s*</div>',
        r.text, re.DOTALL,
    )

    # 각 블록에서 고해상도 URL 추출
    image_urls = []
    for block in img_blocks:
        lazy = re.findall(r'data-lazy-src="([^"]+)"', block)
        if lazy:
            image_urls.append(lazy[0])
        else:
            src = re.findall(r'src="(https://[^"]*pstatic[^"]*)"', block)
            if src:
                image_urls.append(src[0])

    # 중복 제거 (순서 유지)
    seen = set()
    unique_urls = []
    for img_url in image_urls:
        if img_url not in seen:
            seen.add(img_url)
            unique_urls.append(img_url)

    # 이미지 다운로드
    photos = []
    download_headers = {**HEADERS, "Referer": "https://m.blog.naver.com/"}
    for i, img_url in enumerate(unique_urls):
        try:
            r2 = requests.get(img_url, headers=download_headers, timeout=10)
            if r2.status_code == 200 and len(r2.content) > 1000:
                photos.append({
                    "index": i,
                    "url": img_url,
                    "bytes": r2.content,
                    "name": f"photo_{i}.jpg",
                })
        except Exception:
            continue

    return photos


def extract_text_from_post(blog_id: str, log_no: str) -> str:
    """발행된 글에서 텍스트를 추출한다 (기존 글 참고용)."""
    url = f"https://m.blog.naver.com/{blog_id}/{log_no}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    paragraphs = re.findall(
        r'<p class="se-text-paragraph[^"]*"[^>]*>(.*?)</p>',
        r.text, re.DOTALL,
    )
    lines = []
    for p in paragraphs:
        from html import unescape
        cleaned = re.sub(r'<[^>]+>', '', p).strip()
        cleaned = unescape(cleaned)
        if cleaned and cleaned != "\u200b":
            lines.append(cleaned)
    return "\n".join(lines)


def parse_blog_url(url: str) -> tuple[str, str]:
    """블로그 URL에서 blog_id와 log_no를 추출한다.

    지원 형식:
    - https://blog.naver.com/rinx_x/224115890458
    - https://m.blog.naver.com/rinx_x/224115890458
    - blog.naver.com/rinx_x/224115890458
    """
    # URL에서 blog_id와 log_no 추출
    match = re.search(r'blog\.naver\.com/([^/]+)/(\d+)', url)
    if match:
        return match.group(1), match.group(2)

    raise ValueError(f"올바른 네이버 블로그 URL이 아닙니다: {url}")
