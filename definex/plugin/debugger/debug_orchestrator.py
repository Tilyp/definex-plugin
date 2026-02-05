from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from definex.plugin.debugger.remote_debugger import PluginRemoteDebugger


class DebugOrchestrator:
    def __init__(self, console: Console, config_mgr, generator):
        self.console = console
        self.config_mgr = config_mgr
        self.generator = generator

    def start(self, path: Path, env_name: str = None, protocol: str = "ws"):
        """调试生命周期编排"""
        # 1. 环境与配置决议
        push_cfg = self.config_mgr.get_section("push")
        envs = push_cfg.get("environments", {})

        target_env = env_name or push_cfg.get("default")

        # 2. 如果配置缺失，进入交互式引导
        if target_env not in envs or not envs[target_env].get("url"):
            target_env = self._interactive_config(target_env)
            # 重新获取更新后的配置
            envs = self.config_mgr.get_section("push").get("environments", {})

        settings = envs[target_env]

        # 3. 启动底层调试代理
        agent = PluginRemoteDebugger(self.console, self.generator)
        agent.connect(
            root_path=path,
            url=settings["url"],
            token=settings["token"],
            env_label=target_env,
            protocol=protocol
        )

    def _interactive_config(self, env_name):
        """交互式补全 push 配置"""
        name = env_name or "dev"
        self.console.print(f"\n[yellow]⚠️  未发现环境 '{name}' 的配置信息，请先完善：[/yellow]")
        url = Prompt.ask(f"请输入 {name} 环境的 API 地址 (如 http://host/api/v1/upload)")
        token = Prompt.ask(f"请输入 {name} 环境的 Token", password=True)

        # 写入全局配置
        self.config_mgr.set_env_config(name, url, token)
        self.console.print(f"[green]✅ 配置已同步至全局 ~/.definex/config.yaml[/green]\n")
        return name