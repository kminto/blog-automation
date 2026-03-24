"""
API 공통 유틸리티 모듈
API 호출의 에러 처리, 재시도 등 공통 기능을 제공한다.
"""

from typing import Callable, Any


def safe_api_call(func: Callable, *args: Any, **kwargs: Any) -> dict:
    """API 호출을 안전하게 수행하고, 결과를 통일된 형식으로 반환한다."""
    try:
        data = func(*args, **kwargs)
        return {"success": True, "data": data, "error": None}
    except ConnectionError:
        return {
            "success": False,
            "data": None,
            "error": "서버에 연결할 수 없습니다. 네트워크를 확인해주세요.",
        }
    except TimeoutError:
        return {
            "success": False,
            "data": None,
            "error": "요청 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.",
        }
    except RuntimeError as e:
        return {"success": False, "data": None, "error": str(e)}
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"예상치 못한 오류가 발생했습니다: {e}",
        }
