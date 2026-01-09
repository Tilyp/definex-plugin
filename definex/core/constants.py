"""
DefineX 常量定义
集中管理所有魔法数字和配置常量
"""

from enum import Enum
from typing import Final

# ============================================================================
# 错误码定义
# ============================================================================

class ErrorCode(int, Enum):
    """错误码枚举"""
    SUCCESS = 0
    VALIDATION_ERROR = 1001
    PLUGIN_NOT_FOUND = 1002
    CONFIG_ERROR = 1003
    PERMISSION_DENIED = 1004
    RESOURCE_EXHAUSTED = 1005
    TIMEOUT = 1006
    NETWORK_ERROR = 1007
    INTERNAL_ERROR = 1999

# ============================================================================
# 时间常量（秒）
# ============================================================================

class Timeout:
    """超时设置"""
    DEFAULT: Final[int] = 30
    SHORT: Final[int] = 5
    LONG: Final[int] = 300
    CONNECT: Final[int] = 10
    READ: Final[int] = 30

class Interval:
    """间隔时间"""
    HEARTBEAT: Final[int] = 60
    RETRY: Final[int] = 5
    CACHE_REFRESH: Final[int] = 300

# ============================================================================
# 大小限制
# ============================================================================

class SizeLimit:
    """大小限制（字节）"""
    MAX_PLUGIN_SIZE: Final[int] = 10 * 1024 * 1024  # 10MB
    MAX_CONFIG_SIZE: Final[int] = 1 * 1024 * 1024   # 1MB
    MAX_LOG_SIZE: Final[int] = 50 * 1024 * 1024     # 50MB
    MAX_MEMORY_USAGE: Final[int] = 512 * 1024 * 1024  # 512MB

class CountLimit:
    """数量限制"""
    MAX_PLUGINS: Final[int] = 100
    MAX_CONCURRENT_TASKS: Final[int] = 10
    MAX_RECURSION_DEPTH: Final[int] = 50
    MAX_RETRY_ATTEMPTS: Final[int] = 3

# ============================================================================
# 路径常量
# ============================================================================

class Paths:
    """路径配置"""
    PLUGIN_DIR: Final[str] = "plugins"
    CONFIG_DIR: Final[str] = "config"
    LOG_DIR: Final[str] = "logs"
    CACHE_DIR: Final[str] = ".cache"
    TEMP_DIR: Final[str] = "temp"

# ============================================================================
# 网络配置
# ============================================================================

class Network:
    """网络配置"""
    DEFAULT_HOST: Final[str] = "0.0.0.0"
    DEFAULT_PORT: Final[int] = 8000
    MAX_CONNECTIONS: Final[int] = 100
    KEEP_ALIVE_TIMEOUT: Final[int] = 5

# ============================================================================
# 日志级别
# ============================================================================

class LogLevel:
    """日志级别"""
    DEBUG: Final[str] = "DEBUG"
    INFO: Final[str] = "INFO"
    WARNING: Final[str] = "WARNING"
    ERROR: Final[str] = "ERROR"
    CRITICAL: Final[str] = "CRITICAL"

# ============================================================================
# MCP 协议常量
# ============================================================================

class MCP:
    """MCP 协议常量"""
    PROTOCOL_VERSION: Final[str] = "1.0"
    DEFAULT_TOOL_TIMEOUT: Final[int] = 30
    MAX_TOOL_OUTPUT_SIZE: Final[int] = 1024 * 1024  # 1MB

# ============================================================================
# 性能配置
# ============================================================================

class Performance:
    """性能配置"""
    CACHE_SIZE: Final[int] = 1000
    CACHE_TTL: Final[int] = 300  # 5分钟
    BATCH_SIZE: Final[int] = 100
    CHUNK_SIZE: Final[int] = 8192  # 8KB

# ============================================================================
# 安全配置
# ============================================================================

class Security:
    """安全配置"""
    MIN_PASSWORD_LENGTH: Final[int] = 8
    MAX_LOGIN_ATTEMPTS: Final[int] = 5
    SESSION_TIMEOUT: Final[int] = 3600  # 1小时
    TOKEN_EXPIRY: Final[int] = 7 * 24 * 3600  # 7天

# ============================================================================
# 默认值
# ============================================================================

class Defaults:
    """默认值"""
    ENCODING: Final[str] = "utf-8"
    TIMEZONE: Final[str] = "UTC"
    LOCALE: Final[str] = "en_ZH"
    LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
