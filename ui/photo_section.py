"""
촬영 가이드 모듈
카테고리별 촬영 포인트를 카드 형태로 렌더링한다.
"""

import streamlit as st

from modules.photo_manager import get_shot_guide


def render_photo_section():
    """촬영 가이드를 가독성 좋은 카드 형태로 렌더링한다."""
    guide = get_shot_guide()

    st.markdown(
        '<div style="background:#f0f8f0;border-radius:8px;padding:12px 16px;margin-bottom:12px;">'
        '<b>📸 사용법 3단계</b><br>'
        '① 아래 순서대로 사진 찍기<br>'
        '② 앱에서 본문 생성 → 텍스트 복사<br>'
        '③ 네이버 에디터에 붙여넣기 → 📷 자리에 사진 넣기</div>',
        unsafe_allow_html=True,
    )

    # 촬영 가이드를 카테고리별로 묶어서 표시
    categories = {
        "🏪 매장": [s for s in guide if s["slot"] <= 2],
        "🪑 내부": [s for s in guide if 3 <= s["slot"] <= 4],
        "📋 메뉴판": [s for s in guide if s["slot"] == 5],
        "🥢 기본세팅": [s for s in guide if s["slot"] == 6],
        "🍖 메인1": [s for s in guide if 7 <= s["slot"] <= 9],
        "🍖 메인2": [s for s in guide if 10 <= s["slot"] <= 11],
        "🍺 사이드": [s for s in guide if s["slot"] == 12],
        "📸 추가": [s for s in guide if s["slot"] == 13],
    }

    for cat_name, shots in categories.items():
        if not shots:
            continue
        items = " → ".join([f"**{s['label']}**" for s in shots])
        tips = " / ".join([s["tip"] for s in shots])
        st.markdown(f"{cat_name} {items}")
        st.caption(f"💡 {tips}")

    st.markdown("---")
    st.markdown(
        "**본문에서 이렇게 표시됩니다:**\n\n"
        "`📷 1번 사진 - 가게 간판이 보이게 정면에서 한 장`\n\n"
        "→ 네이버 에디터에서 이 자리에 1번 사진을 넣으면 끝!"
    )
