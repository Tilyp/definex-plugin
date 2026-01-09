import inspect
from typing import Annotated, get_origin, get_args, get_type_hints, Required, Literal

from definex.plugin.sdk import DataTypes, MAX_NESTING_DEPTH, PYTHON_TO_SYSTEM_MAP


class SchemaTranslator:

    @staticmethod
    def resolve_type(py_type, depth=0, default_val=inspect.Parameter.empty):
        """
        核心解析方法
        py_type: 类型对象
        depth: 当前递归深度
        default_val: 外部传入的默认值
        """
        if depth > MAX_NESTING_DEPTH:
            return {"type": "INVALID", "error": f"嵌套过深(>{MAX_NESTING_DEPTH}层)"}

        is_required=False
        description = ""
        enum_values = None

        # 1. 处理 Annotated 元数据
        if get_origin(py_type) is Annotated:
            type_args = get_args(py_type)
            py_type = type_args[0]
            metadata = type_args[1:]

            # 提取描述
            if len(metadata) > 0 and isinstance(metadata[0], str):
                description = metadata[0]

            # 提取 Required 标记 (支持 typing.Required 或自定义字符串标记)
            if any(str(m) == 'typing.Required' or m == Required for m in metadata):
                is_required = True

        # 2. 处理 Literal (Enums)
        origin = get_origin(py_type)
        if origin is Literal:
            enum_values = list(get_args(py_type))
            py_type = type(enum_values[0]) if enum_values else str

        # 3. 类型归一化映射
        py_type_name = getattr(py_type, '__name__', str(py_type))
        system_type = PYTHON_TO_SYSTEM_MAP.get(py_type_name, DataTypes.OBJECT)

        # 4. 构建基础 Schema 节点
        schema = {
            "type": system_type,
            "description": description,
        }

        # 只有顶级参数才设置 required 字段
        if depth == 0:
            schema["required"] = is_required

        if enum_values:
            schema["enum"] = enum_values

        # 5. 注入默认值 (过滤掉 inspect 的空标记)
        if default_val is not inspect.Parameter.empty and default_val is not None:
            schema["default"] = default_val

        # 6. 处理自定义类 (OBJECT)
        if system_type == DataTypes.OBJECT and inspect.isclass(py_type):
            if issubclass(py_type, dict):
                return {"type": "INVALID", "error": "禁止直接使用 dict"}

            properties = {}
            required_fields = [] # 类内部字段的 required 列表

            try:
                hints = get_type_hints(py_type, include_extras=True)
                for prop_name, prop_hint in hints.items():
                    # 尝试从类属性获取默认值
                    prop_default = getattr(py_type, prop_name, inspect.Parameter.empty)

                    # 递归解析子属性
                    prop_res = SchemaTranslator.resolve_type(prop_hint, depth + 1, prop_default)

                    # 如果子属性标记了 required: true，加入数组
                    if prop_res.get("required"):
                        required_fields.append(prop_name)
                        # 移除子属性的 required 标记，避免重复
                        if "required" in prop_res:
                            del prop_res["required"]

                    properties[prop_name] = prop_res

                schema["properties"] = properties
                # 类内部的 required 字段
                if required_fields:
                    schema["required_fields"] = required_fields
            except Exception as e:
                return {"type": "INVALID", "error": f"解析类 {py_type_name} 失败: {str(e)}"}

        return schema
