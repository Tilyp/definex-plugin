import functools
from typing import Any, Optional


class DataTypes:
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    BLOB = "blob"
    NULL = "null"

MAX_NESTING_DEPTH = 3
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

ICON_LIBRARY = {
    "1": {"icon": "🛠️", "label": "General Tool"},
    "2": {"icon": "🤖", "label": "AI & LLM"},
    "3": {"icon": "📁", "label": "File Management"},
    "4": {"icon": "🌐", "label": "Web Integration"},
    "5": {"icon": "🗄️", "label": "Database"},
    "6": {"icon": "🛡️", "label": "Security"},
}

class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def action(category="exec", stream=False):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper._is_action = True
        wrapper._action_category = category
        wrapper._is_streaming = stream # 注入流式元数据，标志该 Action 是否为流式输出 (Generator)
        return wrapper
    if callable(category):
        func, category = category, "exec"
        return decorator(func)
    return decorator

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

class BasePlugin:
    pass