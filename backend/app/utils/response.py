import math
from typing import Any

def _sanitize(obj: Any) -> Any:
    """Replace NaN/Inf with None so JSON serialization doesn't crash."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj

def success(data: Any = None, message: str = "ok") -> dict:
    return _sanitize({"code": 0, "data": data, "message": message})

def error(code: int, message: str, data: Any = None) -> dict:
    return _sanitize({"code": code, "data": data, "message": message})
