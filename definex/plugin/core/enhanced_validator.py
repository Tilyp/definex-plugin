"""
增强参数校验器
支持对 action 方法参数进行严格校验
"""

import inspect
import re
from typing import Annotated, Required, Literal
from typing import Any, List, get_type_hints, get_origin, get_args


class ValidationError(ValueError):
    """参数校验错误"""
    def __init__(self, param_name: str, message: str):
        self.param_name = param_name
        self.message = message
        super().__init__(f"参数 '{param_name}' 校验失败: {message}")


class ParameterValidator:
    """参数校验器"""

    # 预定义校验规则
    VALIDATION_RULES = {
        "required": "必填参数",
        "length": "长度限制",
        "range": "数值范围",
        "pattern": "正则表达式",
        "enum": "枚举值",
        "email": "邮箱格式",
        "url": "URL格式",
        "phone": "手机号格式",
    }

    @staticmethod
    def validate_string(value: Any, param_name: str, metadata: List[Any]) -> None:
        """校验字符串参数"""
        if not isinstance(value, str):
            raise ValidationError(param_name, f"必须是字符串类型，实际类型: {type(value).__name__}")

        # 检查必填
        if any(str(m) == 'typing.Required' or m == Required for m in metadata):
            if not value or len(value.strip()) == 0:
                raise ValidationError(param_name, "不能为空")

        # 解析校验规则
        for rule in metadata:
            if isinstance(rule, str):
                # 长度限制
                if "长度" in rule or "length" in rule.lower():
                    match = re.search(r'(d+)-(d+)', rule)
                    if match:
                        min_len, max_len = int(match.group(1)), int(match.group(2))
                        if len(value) < min_len:
                            raise ValidationError(param_name, f"长度不能少于{min_len}字符")
                        if len(value) > max_len:
                            raise ValidationError(param_name, f"长度不能超过{max_len}字符")

                # 正则表达式
                elif "pattern" in rule.lower() or "格式" in rule:
                    pattern_match = re.search(r'pattern:s*(.+)', rule, re.IGNORECASE)
                    if pattern_match:
                        pattern = pattern_match.group(1).strip()
                        if not re.match(pattern, value):
                            raise ValidationError(param_name, f"不符合格式要求: {pattern}")

                # 特定格式校验
                elif "邮箱" in rule or "email" in rule.lower():
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    if not re.match(email_pattern, value):
                        raise ValidationError(param_name, "邮箱格式不正确")

                elif "URL" in rule or "url" in rule.lower():
                    url_pattern = r'^https?://[\w\-]+(\.[\w\-]+)+[/#?]?.*$'
                    if not re.match(url_pattern, value):
                        raise ValidationError(param_name, "URL格式不正确")

                elif "手机号" in rule or "phone" in rule.lower():
                    phone_pattern = r'^1[3-9]\d{9}$'
                    if not re.match(phone_pattern, value):
                        raise ValidationError(param_name, "手机号格式不正确")

    @staticmethod
    def validate_number(value: Any, param_name: str, metadata: List[Any]) -> None:
        """校验数值参数"""
        if not isinstance(value, (int, float)):
            raise ValidationError(param_name, f"必须是数值类型，实际类型: {type(value).__name__}")

        # 检查必填（数值类型通常都有值，但可以检查是否为None）
        if any(str(m) == 'typing.Required' or m == Required for m in metadata):
            if value is None:
                raise ValidationError(param_name, "不能为空")

        # 解析校验规则
        for rule in metadata:
            if isinstance(rule, str):
                # 数值范围
                if "范围" in rule or "range" in rule.lower():
                    match = re.search(r'(d+)-(d+)', rule)
                    if match:
                        min_val, max_val = float(match.group(1)), float(match.group(2))
                        if value < min_val:
                            raise ValidationError(param_name, f"不能小于{min_val}")
                        if value > max_val:
                            raise ValidationError(param_name, f"不能大于{max_val}")

    @staticmethod
    def validate_boolean(value: Any, param_name: str, metadata: List[Any]) -> None:
        """校验布尔参数"""
        if not isinstance(value, bool):
            raise ValidationError(param_name, f"必须是布尔类型，实际类型: {type(value).__name__}")

    @staticmethod
    def validate_enum(value: Any, param_name: str, enum_values: List[Any]) -> None:
        """校验枚举参数"""
        if value not in enum_values:
            raise ValidationError(param_name, f"必须是以下值之一: {enum_values}")

    @staticmethod
    def validate_parameter(param_name: str, param_value: Any, param_type: Any) -> None:
        """校验单个参数"""
        if param_type is None:
            return

        # 提取 Annotated 元数据
        metadata = []
        if get_origin(param_type) is Annotated:
            type_args = get_args(param_type)
            actual_type = type_args[0]
            metadata = list(type_args[1:])
        else:
            actual_type = param_type

        # 检查 Literal 类型
        if get_origin(actual_type) is Literal:
            enum_values = list(get_args(actual_type))
            ParameterValidator.validate_enum(param_value, param_name, enum_values)
            return

        # 根据类型调用相应的校验方法
        type_name = getattr(actual_type, '__name__', str(actual_type))

        if type_name == 'str':
            ParameterValidator.validate_string(param_value, param_name, metadata)
        elif type_name in ['int', 'float']:
            ParameterValidator.validate_number(param_value, param_name, metadata)
        elif type_name == 'bool':
            ParameterValidator.validate_boolean(param_value, param_name, metadata)
        # 可以添加更多类型的校验


class EnhancedActionDecorator:
    """增强的 action 装饰器"""

    def __init__(self, category="exec"):
        self.category = category

    def __call__(self, func):
        """装饰器实现"""
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self._validate_and_execute(func, *args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return self._validate_and_execute(func, *args, **kwargs)

        wrapper = async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
        wrapper._is_action = True
        wrapper._action_category = self.category
        wrapper._enhanced_validation = True

        return wrapper

    def _validate_and_execute(self, func, *args, **kwargs):
        """校验参数并执行函数"""
        # 获取函数签名
        sig = inspect.signature(func)

        # 获取类型提示
        try:
            hints = get_type_hints(func, include_extras=True)
        except Exception:
            hints = {}

        # 绑定参数
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # 校验每个参数
        for param_name, param_value in bound_args.arguments.items():
            if param_name == 'self':
                continue

            param_type = hints.get(param_name)
            if param_type:
                try:
                    ParameterValidator.validate_parameter(param_name, param_value, param_type)
                except ValidationError as e:
                    # 记录校验错误
                    print(f"⚠️ 参数校验警告: {e}")
                    # 可以在这里记录日志或进行其他处理

        # 执行原函数
        if inspect.iscoroutinefunction(func):
            import asyncio
            return asyncio.create_task(func(*args, **kwargs))
        else:
            return func(*args, **kwargs)


# 创建增强的 action 装饰器
def enhanced_action(category="exec"):
    """增强的 action 装饰器工厂函数"""
    return EnhancedActionDecorator(category)


# 向后兼容的装饰器
def action(category="exec"):
    """原始的 action 装饰器（增强版）"""
    def decorator(func):
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 参数校验
            sig = inspect.signature(func)
            hints = get_type_hints(func, include_extras=True)

            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            for param_name, param_value in bound_args.arguments.items():
                if param_name == 'self':
                    continue

                param_type = hints.get(param_name)
                if param_type:
                    try:
                        ParameterValidator.validate_parameter(param_name, param_value, param_type)
                    except ValidationError as e:
                        print(f"⚠️ 参数校验警告: {e}")
                        # 可以选择是否抛出异常
                        # raise

            # 执行原函数
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 参数校验
            sig = inspect.signature(func)
            hints = get_type_hints(func, include_extras=True)

            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            for param_name, param_value in bound_args.arguments.items():
                if param_name == 'self':
                    continue

                param_type = hints.get(param_name)
                if param_type:
                    try:
                        ParameterValidator.validate_parameter(param_name, param_value, param_type)
                    except ValidationError as e:
                        print(f"⚠️ 参数校验警告: {e}")
                        # 可以选择是否抛出异常
                        # raise

            return func(*args, **kwargs)

        wrapper = async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
        wrapper._is_action = True
        wrapper._action_category = category

        return wrapper

    if callable(category):
        func, category = category, "exec"
        return decorator(func)

    return decorator
