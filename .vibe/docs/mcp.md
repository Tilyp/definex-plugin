# MCP 协议集成

## 协议同构

DefineX 原生支持 MCP (Model Context Protocol)，实现:
- Schema 层面 1:1 对齐
- 零转换损耗
- 双向无缝切换

## MCP Tool 定义

DefineX Action → MCP Tool 转换:

```python
# DefineX Action (manifest.yaml)
{
    "name": "greet",
    "description": "向用户打招呼",
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "用户姓名"
            }
        },
        "required": ["name"]
    }
}

# MCP Tool (JSON Schema)
{
    "name": "greet",
    "description": "向用户打招呼",
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "用户姓名"
            }
        },
        "required": ["name"]
    }
}
```

## 类型转换

| DefineX Type | MCP Schema | 说明 |
|---------------|------------|------|
| `string` | `string` | - |
| `number` | `number` | - |
| `boolean` | `boolean` | - |
| `array` | `array` | - |
| `object` | `object` | - |
| `blob` | `string` | 转 Base64 |

## MCP 适配器

```python
# mcp_adapter.py

class MCPAdapter:
    @staticmethod
    def to_mcp_tool(action_meta):
        input_schema = MCPAdapter._clean_schema(
            action_meta.get("inputSchema", {})
        )
        return {
            "name": action_meta["name"],
            "description": action_meta["description"],
            "inputSchema": input_schema
        }
    
    @staticmethod
    def _clean_schema(schema):
        # BLOB → string
        if schema.get("type") == DataTypes.BLOB:
            schema["type"] = "string"
        # 递归处理
        ...
```

## MCP 服务运行

```bash
# Stdio 模式 (本地挂载)
dfx plugin run mcp --protocol stdio

# HTTP 模式
dfx plugin run mcp --protocol http --port 8080

# SSE 模式 (服务端推送)
dfx plugin run mcp --protocol sse --port 8080
```

## FastMCP 集成

```python
# mcp_server.py

class DefineXMCPBridge:
    def serve(self, protocol="stdio", port=8080):
        mcp = FastMCP(
            name=plugin_id,
            host="0.0.0.0",
            port=port
        )
        
        # 注册所有 Action
        for action_meta in self.plugin_runtime.actions:
            self._register_action(mcp, action_meta)
        
        # 启动服务
        mcp.run(transport=protocol)
    
    def _register_action(self, mcp_instance, action_meta):
        tool_config = MCPAdapter.to_mcp_tool(action_meta)
        
        def tool_handler(**kwargs):
            result = self.plugin_runtime.execute(
                action_meta["name"], 
                kwargs
            )
            return json.dumps(result)
        
        mcp_instance.tool(
            name=tool_config["name"],
            description=tool_config["description"]
        )(tool_handler)
```

## 协议选择

| 场景 | 推荐协议 | 说明 |
|------|---------|------|
| Cursor/Claude 挂载 | stdio | 本地进程通信 |
| Web 应用调用 | http | RESTful 风格 |
| 实时推送 | sse | Server-Sent Events |
| 生产部署 | sse | 长连接场景 |
