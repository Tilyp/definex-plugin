import functools
from typing import Any, Optional

MAX_NESTING_DEPTH = 3


class DataTypes:
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    BLOB = "blob"
    NULL = "null"

COLLECTION_TYPES = {list, set, tuple}
PYTHON_TO_SYSTEM_MAP = {
    'str': DataTypes.STRING,
    'int': DataTypes.NUMBER,
    'float': DataTypes.NUMBER,
    'bool': DataTypes.BOOLEAN,
    'list': DataTypes.ARRAY,
    'bytes': DataTypes.BLOB,
    type(None): DataTypes.NULL,
}


def action(category="exec", stream=False):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs): return func(*args, **kwargs)
        wrapper._is_action = True
        wrapper._action_category = category
        wrapper._is_streaming = stream
        return wrapper
    return decorator(category) if callable(category) else decorator


class BasePlugin:
    def __init__(self, runtime_handle=None):
        self.runtime = runtime_handle


class StreamChunk:
    """流式响应的最小单元"""
    def __init__(self, delta: Any, index: int = 0, is_last: bool = False, metadata: Optional[dict] = None):
        self.delta = delta      # 本次增量内容 (可以是字符串、对象片断)
        self.index = index      # 序列号
        self.is_last = is_last  # 是否为结束包
        self.metadata = metadata or {}

    def to_dict(self):
        return {
            "delta": self.delta,
            "index": self.index,
            "is_last": self.is_last,
            "metadata": self.metadata
        }
