"""
입력 검증 모듈
사용자 입력값을 검증하고 정제한다.
"""

import os
from dotenv import load_dotenv


def validate_env() -> list[str]:
    """필수 환경변수가 모두 설정되어 있는지 확인한다."""
    load_dotenv()
    required_keys = [
        "OPENAI_API_KEY",
        "NAVER_CLIENT_ID",
        "NAVER_CLIENT_SECRET",
        "NAVER_AD_API_KEY",
        "NAVER_AD_SECRET_KEY",
        "NAVER_AD_CUSTOMER_ID",
    ]
    missing = [k for k in required_keys if not os.getenv(k)]
    return missing


def validate_restaurant_input(
    name: str,
    regions: str,
    menus: str,
) -> dict:
    """음식점 입력값을 검증하고 에러 메시지를 반환한다."""
    errors = []

    if not name or not name.strip():
        errors.append("음식점 이름을 입력해주세요.")

    if not regions or not regions.strip():
        errors.append("지역을 하나 이상 입력해주세요.")

    if not menus or not menus.strip():
        errors.append("대표 메뉴를 하나 이상 입력해주세요.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def parse_comma_separated(text: str) -> list[str]:
    """쉼표로 구분된 문자열을 정제된 리스트로 변환한다."""
    if not text:
        return []
    items = [item.strip() for item in text.split(",")]
    return [item for item in items if item]
