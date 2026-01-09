import sys
from typing import Literal
import json

from mcp.server import FastMCP
from rich.console import Console

from definex.plugin.runtime import PluginRuntime
from definex.plugin.mcp_adapter import MCPAdapter

class DefineXMCPBridge:
    def __init__(self, console: Console, plugin_runtime : PluginRuntime):
        self.console = console
        self.plugin_runtime = plugin_runtime

    def serve(self, protocol: Literal["stdio", "sse", "http"] = "stdio", port=8080):

        plugin_info = self.plugin_runtime.manifest
        plugin_id = plugin_info["id"]
        mcp = FastMCP(
            name=plugin_id,
            host="0.0.0.0",
            port=port
        )

        # 注册 Action 到 MCP
        for action_meta in self.plugin_runtime.actions:
            self._register_action(mcp, action_meta)

        # 协议分发
        if protocol == "http":
            protocol = "streamable-http"
        mcp.run(transport=protocol)

    def _register_action(self, mcp_instance, action_meta):
        """将单个 Action 注册为 MCP Tool"""
        mcp_config = MCPAdapter.to_mcp_tool(action_meta)
        action_name = mcp_config["name"]
        is_streaming = action_meta.get("is_streaming", False)

        # 定义通用处理器
        def tool_handler(**kwargs):
            try:
                if is_streaming:
                    # 如果是流式 Action
                    full_result = []
                    for chunk in self.plugin_runtime.execute_stream(action_name, kwargs):
                        # MCP 目前对 Tool Call 的实时流支持有限，
                        # 通常汇聚为最终结果或通过 Resource 发送
                        full_result.append(str(chunk["delta"]))
                    return "".join(full_result)
                else:
                    # 同步调用
                    result = self.plugin_runtime.execute(action_name, kwargs)
                    # 序列化为字符串返回给 AI
                    return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                return f"Error executing {action_name}: {str(e)}"

        # 注入到 FastMCP 注册表
        mcp_instance.tool(
            name=mcp_config["name"],
            description=mcp_config["description"]
        )(tool_handler)