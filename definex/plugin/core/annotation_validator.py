"""
统一的参数注解校验工具

提供不同层次的参数注解校验：
1. 装饰器级别：validate_annotated_params - 实时校验方法参数
2. Action级别：validate_actions_annotations - 批量校验扫描得到的Action
"""

import functools
import inspect
import sys
from typing import get_type_hints, get_origin, get_args, Annotated, Any, Dict, List

from rich.console import Console

console = Console()


class AnnotationValidator:
    """参数注解校验器"""

    @staticmethod
    def validate_method_params(func) -> List[str]:
        """
        校验方法的参数注解

        Args:
            func: 要校验的函数或方法

        Returns:
            List[str]: 错误信息列表，为空表示通过
        """
        sig = inspect.signature(func)
        errors = []

        for param_name, param in sig.parameters.items():
            # 跳过self参数
            if param_name == 'self':
                continue

            try:
                type_hints = get_type_hints(func, include_extras=True)

                if param_name in type_hints:
                    type_hint = type_hints[param_name]

                    # 检查是否是Annotated类型
                    if get_origin(type_hint) is Annotated:
                        annotated_args = get_args(type_hint)
                        if len(annotated_args) < 2:
                            errors.append(f"参数 '{param_name}': Annotated注解必须包含类型和描述")
                        else:
                            description = annotated_args[1] if len(annotated_args) > 1 else None
                            if not isinstance(description, str) or not description.strip():
                                errors.append(f"参数 '{param_name}': 缺少有效的描述信息")
                    else:
                        errors.append(f"参数 '{param_name}': 必须使用Annotated类型注解")
                else:
                    errors.append(f"参数 '{param_name}': 缺少类型注解")
            except Exception as e:
                errors.append(f"参数 '{param_name}': 类型注解格式错误 - {str(e)}")

        return errors

    @staticmethod
    def validate_actions_annotations(actions: List[Dict[str, Any]]) -> List[str]:
        """
        批量校验Action的参数注解

        Args:
            actions: Action列表，来自扫描器

        Returns:
            List[str]: 错误信息列表，为空表示通过
        """
        errors = []

        for action in actions:
            action_name = action.get("name", "Unknown")
            validation_warnings = action.get("_validation_warnings", [])

            # 检查参数注解相关的警告
            param_warnings = [w for w in validation_warnings
                            if w.get("type") in ["parameter_annotation", "parameter_description"]]

            for warning in param_warnings:
                if warning["type"] == "parameter_annotation":
                    errors.append(f"Action '{action_name}': {warning['message']}")
                elif warning["type"] == "parameter_description":
                    errors.append(f"Action '{action_name}': {warning['message']}")

        return errors

    @staticmethod
    def print_validation_errors(errors: List[str], context: str = "") -> None:
        """
        打印校验错误信息

        Args:
            errors: 错误信息列表
            context: 上下文信息（如方法名）
        """
        if errors:
            console.print(f"\n[bold red]❌ 参数注解校验失败[/bold red]")
            if context:
                console.print(f"[yellow]上下文:[/yellow] {context}")
            console.print(f"[yellow]问题:[/yellow]")
            for error in errors:
                console.print(f"  • {error}")
            console.print(f"\n[dim]提示: 所有参数必须使用Annotated[类型, \"描述\"]格式进行注解[/dim]")

    @staticmethod
    def print_annotation_guidance() -> None:
        """打印参数注解指导"""
        console.print("\n[bold yellow]💡 参数注解规范:[/bold yellow]")
        console.print("    1. 所有参数必须使用 Annotated[类型, \"描述\"] 格式")
        console.print("    2. Annotated 注解必须包含描述信息")
        console.print("    3. 示例: Annotated[str, \"用户名\"]")


# 装饰器函数
def validate_annotated_params(func):
    """
    装饰器：强制校验Annotated参数注解

    使用示例：
        @validate_annotated_params
        def my_method(param: Annotated[str, "参数描述"]): ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        errors = AnnotationValidator.validate_method_params(func)

        if errors:
            AnnotationValidator.print_validation_errors(errors, func.__name__)
            sys.exit(1)

        return func(*args, **kwargs)

    return wrapper


# 快捷函数
def validate_actions(actions: List[Dict[str, Any]]) -> List[str]:
    """快捷函数：校验Action参数注解"""
    return AnnotationValidator.validate_actions_annotations(actions)


def print_errors_with_guidance(errors: List[str], context: str = "") -> bool:
    """
    打印错误并提供指导

    Args:
        errors: 错误信息列表
        context: 上下文信息

    Returns:
        bool: 是否通过校验（True表示通过）
    """
    if errors:
        AnnotationValidator.print_validation_errors(errors, context)
        AnnotationValidator.print_annotation_guidance()
        return False
    return True

# 导出所有公共函数
__all__ = [
    'validate_actions',
    'print_errors_with_guidance',
    'AnnotationValidator'
]
