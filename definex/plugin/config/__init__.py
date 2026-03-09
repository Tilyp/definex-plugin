"""
DefineX 配置管理模块

架构：
- ConfigManager: 主入口，聚合子管理器
  └── PushManager: 发布环境管理
- FileStorage: 配置文件存储（YAML）
- ConfigEncryption: 敏感信息加密
"""

from .encryption import ConfigEncryption
from .manager import ConfigManager
from .models import (
    PushEnvironment,
    PushConfig
)
from .push_manager import PushManager
from ..storage.storage import FileStorage

__version__ = "0.1.0"
__all__ = [

    # 数据模型
    "PushEnvironment",
    "PushConfig",

    # 基础设施
    "ConfigEncryption",
    "FileStorage",

    # 子管理器
    "PushManager",

    # 主管理器
    "ConfigManager",
]
