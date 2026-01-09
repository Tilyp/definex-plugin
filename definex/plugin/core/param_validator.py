"""
参数校验装饰器模块 - 简化版

使用统一的AnnotationValidator工具类
"""

from definex.plugin.core.annotation_validator import (
    validate_actions,
    print_errors_with_guidance
)

# 导出相同的接口，保持向后兼容
__all__ = [
    'validate_actions',
    'print_errors_with_guidance'
]
