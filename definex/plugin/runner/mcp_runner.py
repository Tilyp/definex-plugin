"""
DefineX MCP运行器 - 专门处理MCP模式执行逻辑
"""
from typing import Any, Dict, Literal

from rich.console import Console

from definex.plugin.mcp_server import DefineXMCPBridge
from plugin import PluginRuntime


class MCPRunner:
    """MCP运行器 - 专门处理MCP模式的执行逻辑"""

    def __init__(self, console: Console, plugin_runtime: PluginRuntime):
        """
        初始化MCP运行器

        Args:
            console: 控制台输出
            manifest_gen: 契约生成器
        """
        self.console = console
        self.plugin_runtime = plugin_runtime

    def run(self, protocol: Literal["stdio", "sse", "http"] = "stdio", port: int = 8080) -> Any:
        """
        执行MCP模式运行
        Args:
            path: 插件路径
            protocol: 协议类型
            port: 端口号
            watch: 是否监控

        Returns:
            运行结果
        """
        # 具体的MCP执行逻辑
        bridge = DefineXMCPBridge(self.console, self.plugin_runtime)
        bridge.serve(protocol, port)

    def get_supported_protocols(self) -> Dict[str, str]:
        """获取支持的协议列表"""
        return {
            "stdio": "标准输入输出",
            "http": "HTTP服务"
        }

    def validate_protocol(self, protocol: str) -> bool:
        """验证协议是否支持"""
        return protocol in ["stdio", "http"]

