"""
DefineX 异常处理系统
定义完整的异常类型树，支持细粒度的异常捕获和处理
"""


# ============================================================================
# 基础异常
# ============================================================================

class DefinexException(Exception):
    """DefineX 基础异常，所有其他异常的父类"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        """
        初始化异常
        
        Args:
            message: 错误消息
            error_code: 错误代码（用于国际化和错误跟踪）
            details: 附加错误信息
        """
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """格式化错误消息"""
        msg = f"[{self.error_code}] {self.message}"
        if self.details:
            details_str = "; ".join(f"{k}={v}" for k, v in self.details.items())
            msg += f" ({details_str})"
        return msg


# ============================================================================
# 扫描器异常
# ============================================================================

class ScannerException(DefinexException):
    """代码扫描器异常"""
    pass


class SyntaxErrorException(ScannerException):
    """Python 文件语法错误"""
    pass


class ModuleLoadException(ScannerException):
    """模块加载失败"""
    pass


class ActionExtractionException(ScannerException):
    """Action 提取失败"""
    pass


# ============================================================================
# 验证器异常
# ============================================================================

class ValidationException(DefinexException):
    """合规性验证异常"""
    pass


class SchemaMismatchException(ValidationException):
    """源码与契约不匹配"""
    pass


class TypeValidationException(ValidationException):
    """类型验证失败"""
    pass


class NestingDepthException(ValidationException):
    """嵌套深度超限"""
    pass


class BlackboxTypeException(ValidationException):
    """检测到黑盒类型（dict/Any）"""
    pass


class MissingDocstringException(ValidationException):
    """缺少文档字符串"""
    pass


class RequirementVersionException(ValidationException):
    """依赖版本号不合规"""
    pass


# ============================================================================
# 构建器异常
# ============================================================================

class BuildException(DefinexException):
    """构建异常"""
    pass


class DependencyInstallException(BuildException):
    """依赖安装失败"""
    pass


class PackagingException(BuildException):
    """打包失败"""
    pass


class CompressionException(BuildException):
    """压缩失败"""
    pass


# ============================================================================
# 运行时异常
# ============================================================================

class RuntimeException(DefinexException):
    """运行时异常"""
    pass


class ActionNotFoundExceptionEx(RuntimeException):
    """Action 不存在"""
    pass


class ExecutionTimeoutException(RuntimeException):
    """执行超时"""
    pass


class ActionExecutionException(RuntimeException):
    """Action 执行失败"""
    pass


class ResourceExhaustedException(RuntimeException):
    """资源耗尽"""
    pass


# ============================================================================
# 配置异常（复用 config 模块中的异常）
# ============================================================================

class ConfigException(DefinexException):
    """配置异常基类"""
    pass


class ConfigEncryptionException(ConfigException):
    """配置加密/解密异常"""
    pass


class ConfigValidationException(ConfigException):
    """配置验证异常"""
    pass


class ConfigNotFoundException(ConfigException):
    """配置不存在异常"""
    pass


class ModelNotFoundException(ConfigException):
    """模型不存在异常"""
    pass


# ============================================================================
# 发布异常
# ============================================================================

class PublishException(DefinexException):
    """发布异常"""
    pass


class UploadException(PublishException):
    """上传失败"""
    pass


class AuthenticationException(PublishException):
    """认证失败"""
    pass


class ServerException(PublishException):
    """服务器错误"""
    pass


# ============================================================================
# AI/聊天异常
# ============================================================================

class AIException(DefinexException):
    """AI 相关异常"""
    pass


class LLMConnectionException(AIException):
    """LLM 连接失败"""
    pass


class LLMException(AIException):
    """LLM 调用异常"""
    pass


class CodeGenerationException(AIException):
    """代码生成失败"""
    pass


# ============================================================================
# 工具异常
# ============================================================================

class ToolException(DefinexException):
    """工具异常"""
    pass


class FileOperationException(ToolException):
    """文件操作异常"""
    pass


class DirectoryException(ToolException):
    """目录操作异常"""
    pass


# ============================================================================
# 异常映射（用于异常处理和转换）
# ============================================================================

EXCEPTION_HIERARCHY = {
    "DefinexException": {
        "ScannerException": [
            "SyntaxErrorException",
            "ModuleLoadException",
            "ActionExtractionException"
        ],
        "ValidationException": [
            "SchemaMismatchException",
            "TypeValidationException",
            "NestingDepthException",
            "BlackboxTypeException",
            "MissingDocstringException",
            "RequirementVersionException"
        ],
        "BuildException": [
            "DependencyInstallException",
            "PackagingException",
            "CompressionException"
        ],
        "RuntimeException": [
            "ActionNotFoundExceptionEx",
            "ExecutionTimeoutException",
            "ActionExecutionException",
            "ResourceExhaustedException"
        ],
        "ConfigException": [
            "ConfigEncryptionException",
            "ConfigValidationException",
            "ConfigNotFoundException",
            "ModelNotFoundException"
        ],
        "PublishException": [
            "UploadException",
            "AuthenticationException",
            "ServerException"
        ],
        "AIException": [
            "LLMConnectionException",
            "LLMException",
            "CodeGenerationException"
        ],
        "ToolException": [
            "FileOperationException",
            "DirectoryException"
        ]
    }
}


# ============================================================================
# 异常处理工具函数
# ============================================================================

def convert_to_definex_exception(exc: Exception) -> DefinexException:
    """
    将标准 Python 异常转换为 DefineX 异常
    
    Args:
        exc: Python 异常对象
    
    Returns:
        DefinexException 子类实例
    """
    exc_type = type(exc).__name__
    message = str(exc)
    
    mapping = {
        "SyntaxError": SyntaxErrorException,
        "ImportError": ModuleLoadException,
        "ModuleNotFoundError": ModuleLoadException,
        "FileNotFoundError": FileOperationException,
        "PermissionError": FileOperationException,
        "OSError": DirectoryException,
        "ValueError": TypeValidationException,
        "TypeError": TypeValidationException,
        "TimeoutError": ExecutionTimeoutException,
        "ConnectionError": LLMConnectionException,
    }
    
    exception_class = mapping.get(exc_type, DefinexException)
    
    return exception_class(
        message,
        error_code=exc_type,
        details={"original_exception": exc_type}
    )


def wrap_exception(func):
    """
    异常包装装饰器
    自动将异常转换为 DefinexException
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DefinexException:
            # 已经是 DefineX 异常，直接抛出
            raise
        except Exception as e:
            # 转换为 DefineX 异常
            raise convert_to_definex_exception(e) from e
    return wrapper


# ============================================================================
# 异常日志记录
# ============================================================================

def format_exception_for_logging(exc: DefinexException, include_traceback: bool = False) -> str:
    """
    格式化异常用于日志记录
    
    Args:
        exc: DefineX 异常
        include_traceback: 是否包含完整堆栈跟踪
    
    Returns:
        格式化的日志字符串
    """
    import traceback
    
    log_msg = f"""
    Exception Type: {type(exc).__name__}
    Error Code: {exc.error_code}
    Message: {exc.message}
    Details: {exc.details}
    """
    
    if include_traceback:
        log_msg += f"\nTraceback:\n{traceback.format_exc()}"
    
    return log_msg


__all__ = [
    # 基础异常
    "DefinexException",
    
    # 扫描器异常
    "ScannerException",
    "SyntaxErrorException",
    "ModuleLoadException",
    "ActionExtractionException",
    
    # 验证器异常
    "ValidationException",
    "SchemaMismatchException",
    "TypeValidationException",
    "NestingDepthException",
    "BlackboxTypeException",
    "MissingDocstringException",
    "RequirementVersionException",
    
    # 构建器异常
    "BuildException",
    "DependencyInstallException",
    "PackagingException",
    "CompressionException",
    
    # 运行时异常
    "RuntimeException",
    "ActionNotFoundExceptionEx",
    "ExecutionTimeoutException",
    "ActionExecutionException",
    "ResourceExhaustedException",
    
    # 配置异常
    "ConfigException",
    "ConfigEncryptionException",
    "ConfigValidationException",
    "ConfigNotFoundException",
    "ModelNotFoundException",
    
    # 发布异常
    "PublishException",
    "UploadException",
    "AuthenticationException",
    "ServerException",
    
    # AI 异常
    "AIException",
    "LLMConnectionException",
    "LLMException",
    "CodeGenerationException",
    
    # 工具异常
    "ToolException",
    "FileOperationException",
    "DirectoryException",
    
    # 工具函数
    "convert_to_definex_exception",
    "wrap_exception",
    "format_exception_for_logging",
]
