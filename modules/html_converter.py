"""
HTML 변환 모듈
생성된 블로그 본문을 네이버 스마트에디터 호환 HTML로 변환한다.
Ctrl+V로 붙여넣으면 서식이 유지되도록 한다.
"""

import re


def blog_text_to_html(text: str) -> str:
    """블로그 텍스트를 네이버 에디터 호환 HTML로 변환한다."""
    lines = text.split("\n")
    html_parts = []
    photo_counter = 0  # 사진 번호 카운터

    for line in lines:
        stripped = line.strip()

        # 빈 줄 → 여백
        if not stripped:
            html_parts.append('<p><br></p>')
            continue

        # [사진: 설명] → 사진 자리 표시
        if stripped.startswith("[사진") or stripped.startswith("[움짤"):
            is_gif = stripped.startswith("[움짤")
            tag = "움짤" if is_gif else "사진"
            desc = stripped.replace(f"[{tag}:", "").replace(f"[{tag}]", "").rstrip("]").strip()
            photo_counter += 1
            icon = "🎬" if is_gif else "📷"
            html_parts.append(
                f'<div style="background:{"#fff8e1" if is_gif else "#f5f5f5"};'
                f'border:2px dashed {"#ff9800" if is_gif else "#ccc"};'
                f'padding:30px 20px;text-align:center;margin:16px 0;'
                f'border-radius:8px;color:#666;font-size:14px;">'
                f'<b style="font-size:18px;">{icon} {photo_counter}번 {tag}</b><br>'
                f'<span style="color:#999;">{desc or "사진 삽입"}</span></div>'
            )
            continue

        # [운영정보] 블록 시작
        if stripped == "[운영정보]":
            html_parts.append(
                '<div style="background:#fafafa;border-left:4px solid #03c75a;'
                'padding:16px 20px;margin:16px 0;border-radius:4px;'
                'font-size:15px;line-height:2;">'
                '<b style="font-size:16px;">📍 운영정보</b><br>'
            )
            continue

        # 운영정보 항목 (위치 :, 운영시간 : 등)
        if re.match(r"^(위치|운영시간|라스트오더|전화번호|예약|포장|배달|화장실|편의사항)\s*:", stripped):
            key, value = stripped.split(":", 1)
            html_parts.append(f'{key.strip()} : {value.strip()}<br>')
            continue

        # 이모지 소제목 (📍, 🍣, ✨, ❤️, 🔚, 🏷, 🅿️, 🔥 등으로 시작)
        if _is_emoji_heading(stripped):
            html_parts.append(
                f'<p style="font-size:18px;font-weight:bold;'
                f'margin-top:28px;margin-bottom:8px;">{stripped}</p>'
            )
            continue

        # 해시태그 줄 (#으로 시작하는 태그가 3개 이상)
        hashtag_count = len(re.findall(r"#\S+", stripped))
        if hashtag_count >= 3:
            html_parts.append(
                f'<p style="color:#03c75a;font-size:14px;'
                f'line-height:1.8;margin-top:12px;">{stripped}</p>'
            )
            continue

        # 일반 텍스트
        html_parts.append(
            f'<p style="font-size:16px;line-height:1.8;'
            f'margin:4px 0;">{stripped}</p>'
        )

    # 운영정보 블록 닫기 (열린 div가 있으면)
    html_str = "\n".join(html_parts)
    if '<div style="background:#fafafa' in html_str:
        # 운영정보 블록 다음 빈 줄에서 닫기
        html_str = _close_info_block(html_str)

    return html_str


def _is_emoji_heading(text: str) -> bool:
    """이모지로 시작하는 소제목인지 판단한다."""
    if not text:
        return False

    # 소제목 전용 이모지 목록 (본문 이모지와 구분)
    heading_emojis = [
        "📍", "🍣", "🍶", "✨", "❤️", "🔚", "🏷", "🅿️", "🔥",
        "⭐️", "⭐", "💫", "🏪", "🍽",
    ]

    for emoji in heading_emojis:
        if text.startswith(emoji):
            return True

    return False


def _close_info_block(html: str) -> str:
    """운영정보 div 블록을 적절한 위치에서 닫는다."""
    # 운영정보 블록 시작 이후, 빈 줄(<p><br></p>)이 나오면 그 전에 닫기
    parts = html.split("\n")
    result = []
    in_info_block = False

    for part in parts:
        if 'background:#fafafa' in part:
            in_info_block = True
            result.append(part)
            continue

        if in_info_block and '<p><br></p>' in part:
            result.append('</div>')
            result.append(part)
            in_info_block = False
            continue

        result.append(part)

    # 블록이 닫히지 않았으면 마지막에 닫기
    if in_info_block:
        result.append('</div>')

    return "\n".join(result)


def wrap_full_html(title: str, body_html: str, hashtags: str = "") -> str:
    """전체 HTML 문서로 감싼다. (미리보기/다운로드용)"""
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
body {{ font-family: 'Noto Sans KR', sans-serif; max-width: 720px; margin: 0 auto; padding: 20px; }}
</style>
</head>
<body>
<h2>{title}</h2>
{body_html}
{f'<p style="color:#03c75a;font-size:14px;margin-top:20px;">{hashtags}</p>' if hashtags else ''}
</body>
</html>"""
