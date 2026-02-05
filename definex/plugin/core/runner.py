"""
DefineX 插件运行协调器 - 优化版本
职责：只做运行模式分发和协调，不包含具体执行逻辑
"""
from typing import Any, Dict, Optional

from rich.console import Console

from definex.plugin.runner.mcp_runner import MCPRunner
from definex.plugin.runner.native_runner import NativeRunner
from definex.plugin.runtime import PluginRuntime


class RunnerCoordinator:
    """运行协调器 - 只负责模式分发和组件协调"""

    def __init__(self, console: Console, path: str):
        """
        初始化运行协调器

        Args:
            console: 控制台输出
            manifest_gen: 契约生成器
        """
        self.console = console
        self.project_root = path
        self.plugin_runtime = PluginRuntime(self.project_root)


    def run(self, mode: str = "native", action: Optional[str] = None,
            params_json: Optional[str] = None, protocol: str = "stdio",
            port: int = 8080, watch: bool = False, repl: bool = False,
            debug: bool = False) -> Any:
        """
        运行入口分发 - 只做模式分发，不包含具体逻辑

        Args:
            mode: 运行模式 (native/mcp)
            action: 指定执行的action
            params_json: 参数JSON字符串
            protocol: 协议类型
            port: 端口号
            watch: 是否监控
            repl: 是否交互模式
            debug: 是否调试模式

        Returns:
            运行结果
        """

        # 模式分发 - 只做协调，具体逻辑在专门的运行器中
        if mode == "mcp":
            mcp_runner = MCPRunner(self.console, self.plugin_runtime)
            return mcp_runner.run(
                protocol=protocol,
                port=port,
            )
        else:
            native_runner = NativeRunner(self.console, self.plugin_runtime)
            return native_runner.run(
                action=action,
                params_json=params_json,
                watch=watch,
                repl=repl,
                debug=debug
            )

    def list_supported_modes(self) -> Dict[str, str]:
        """列出支持的运行模式"""
        return {
            "native": "原生模式 - 直接执行插件",
            "mcp": "MCP模式 - 通过MCP协议运行"
        }

    def validate_mode(self, mode: str) -> bool:
        """验证运行模式是否支持"""
        return mode in ["native", "mcp"]

# ==================== 工厂函数（保持向后兼容） ====================
class PluginRunner(RunnerCoordinator):
    """向后兼容的别名"""
    pass

