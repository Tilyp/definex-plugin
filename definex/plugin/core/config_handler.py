"""
统一的配置处理器

消除 dfx plugin config 和 dfx plugin guide 中的冗余配置逻辑
提供统一的配置接口，支持命令行和交互式两种方式
"""

from typing import Dict, Any, Optional

from rich.console import Console

from definex.plugin.config.manager import ConfigManager
from definex.plugin.config.models import PushConfig
from definex.plugin.core.guide.handlers import PushHandler
from definex.plugin.core.guide.views import UIManager


class UnifiedConfigHandler:
    """统一的配置处理器"""

    def __init__(self, console: Console, config_mgr: ConfigManager):
        """
        初始化配置处理器

        Args:
            console: 控制台输出
            config_mgr: 配置管理器
        """
        self.console = console
        self.config_mgr = config_mgr

    # ===== Push配置 =====

    def configure_push(self,
                      env: Optional[str] = None,
                      url: Optional[str] = None,
                      token: Optional[str] = None,
                      default: Optional[str] = None,
                      interactive: bool = False) -> None:
        """
        配置发布环境（统一方法）

        Args:
            env: 环境名称
            url: 发布地址
            token: 认证令牌
            default: 是否设为默认环境
            interactive: 是否交互式模式
        """
        self.show_config_status("push")
        if interactive:
            self._configure_push_interactive()
        else:
            self._configure_push_cli(env, url, token, default)

    def _configure_push_cli(self,
                           env: Optional[str],
                           url: Optional[str],
                           token: Optional[str],
                           default: Optional[str]) -> bool:
        """命令行模式配置 Push"""
        try:
            env_name = env or "default"

            # 更新环境配置
            self.config_mgr.update_environment(
                env_name=env_name,
                url=url or "",
                token=token or "",
                description=f"CLI configured environment: {env_name}",
                timeout=30,
                enabled=True
            )

            # 设置默认环境
            if default:
                push_config = self.config_mgr.get_push_config()
                push_config.default_environment = env_name
                self.config_mgr.save_push_config(push_config)

            self.console.print(f"[green]✅ 发布环境配置已更新：{env_name}[/green]")
            if default:
                self.console.print(f"[cyan]📌 已设为默认环境[/cyan]")
            return True

        except Exception as e:
            self.console.print(f"[red]❌ 发布环境配置失败：{e}[/red]")
            return False

    def _configure_push_interactive(self) -> None:
        """交互式模式配置 Push"""

        # 使用现有的 PushHandler
        ui = UIManager(self.console)
        handler = PushHandler(ui, self.config_mgr)
        try:
            handler.show_menu()
            self.console.print("[green]✅ 发布环境配置完成[/green]")
        except KeyboardInterrupt:
            self.console.print("[yellow]👋 操作已取消[/yellow]")
        except Exception as e:
            self.console.print(f"[red]❌ 交互式配置失败：{e}[/red]")

    # ===== 通用配置方法 =====

    def show_config_status(self, section: Optional[str] = None) -> None:
        """
        显示配置状态

        Args:
            section: 配置分区（push），None表示显示所有
        """
        self.console.print("[bold cyan]📋 配置状态[/bold cyan]")
        self.console.print("-" * 40)

        if section is None or section == "push":
            self._show_push_status()

    def _show_push_status(self) -> None:
        """显示 Push配置状态"""
        push_config = self.config_mgr.get_push_config()

        self.console.print("[bold]🚀 发布配置:[/bold]")
        if push_config.default_environment:
            self.console.print(f"  默认环境：[magenta]{push_config.default_environment}[/magenta]")
        else:
            self.console.print("  默认环境：[yellow]未设置[/yellow]")

        if push_config.environments:
            self.console.print(f"  环境数量：{len(push_config.environments)}")
            for env_name, env in push_config.environments.items():
                status = "✅" if env.enabled else "❌"
                self.console.print(f"  {status} {env_name}: {env.url}")
        else:
            self.console.print("  环境数量：[yellow]0[/yellow]")
        self.console.print("")


# 工厂函数
def create_config_handler(console: Console, config_mgr: ConfigManager) -> UnifiedConfigHandler:
    """创建统一的配置处理器实例"""
    return UnifiedConfigHandler(console, config_mgr)
