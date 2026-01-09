from definex.plugin.sdk import DataTypes

class MCPAdapter:

    @staticmethod
    def to_mcp_tool(action_meta):
        """
        将 DefineX 的 Action 元数据转换为完美的 MCP Tool 定义
        """
        # 1. 提取并清理 inputSchema
        # 因为我们的 inputSchema 已经是标准的 JSON Schema 结构了，
        # 所以大部分时候可以直接用，但要处理 BLOB 等特殊类型。
        input_schema = MCPAdapter._clean_schema(action_meta.get("inputSchema", {}))

        return {
            "name": action_meta["name"],
            "description": action_meta["description"],
            "inputSchema": input_schema
        }



    @staticmethod
    def _clean_schema(schema):
        """递归清理并标准化 Schema 以兼容标准 JSON Schema (MCP 规范)"""
        if not isinstance(schema, dict):
            return schema

        new_schema = schema.copy()
        dfx_type = schema.get("type")

        # 核心映射：处理 DefineX 特有类型
        if dfx_type == DataTypes.BLOB:
            new_schema["type"] = "string"
            new_schema["description"] = f"(Binary Data/Base64) {schema.get('description', '')}"

        # 递归处理对象属性
        if "properties" in new_schema:
            new_schema["properties"] = {
                k: MCPAdapter._clean_schema(v)
                for k, v in new_schema["properties"].items()
            }

        # 递归处理数组项
        if "item_schema" in new_schema:
            new_schema["items"] = MCPAdapter._clean_schema(new_schema.pop("item_schema"))

        # 移除 DefineX 内部使用的冗余字段
        new_schema.pop("location", None)
        new_schema.pop("raw_py_type", None)
        new_schema.pop("error", None)

        return new_schema