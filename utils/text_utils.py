"""
텍스트 유틸리티 모듈
텍스트 정제, 포맷팅 관련 공통 함수를 제공한다.
"""


def clean_whitespace(text: str) -> str:
    """연속 공백을 단일 공백으로 정리한다."""
    return " ".join(text.split())


def remove_special_chars(text: str) -> str:
    """제목에 부적합한 특수문자를 제거한다."""
    special_chars = "!@#$%^&*()[]{}|\\<>~`"
    result = text
    for char in special_chars:
        result = result.replace(char, "")
    return result.strip()


def truncate_text(text: str, max_length: int = 100) -> str:
    """텍스트를 지정된 길이로 자르고 말줄임표를 추가한다."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def format_number(num: int) -> str:
    """숫자를 한국식 표기로 포맷한다. (예: 12,345)"""
    return f"{num:,}"
