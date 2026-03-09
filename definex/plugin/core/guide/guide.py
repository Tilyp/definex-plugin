"""
交互式引导的主协调器
负责菜单循环和流程控制
"""
from pathlib import Path
from typing import Optional

from rich.console import Console

from definex.plugin.config import ConfigManager
from definex.plugin.core.config_handler import create_config_handler
from .handlers import ProjectHandler, StatusHandler
from .views import UIManager


class InteractiveGuide:
    """
    交互式引导协调器

    职责：
    1. 初始化 UI 和各个处理器
    2. 驱动主菜单循环
    3. 流程控制和异常处理
    """

    def __init__(self, console: Console, config_mgr: ConfigManager, root_path: Optional[Path] = None):
        """
        初始化引导

        Args:
            console: Rich Console 实例
            config_mgr: 配置管理器
            root_path: 项目根目录
        """
        self.console = console
        self.config_mgr = config_mgr
        self.root_path = root_path or Path.cwd()

        # 初始化 UI 管理器
        self.ui = UIManager(console)

        # 初始化统一配置处理器
        self.config_handler = create_config_handler(console, config_mgr)

        # 初始化其他处理器
        self.project_handler = ProjectHandler(self.ui, config_mgr)
        self.status_handler = StatusHandler(self.ui, config_mgr)

    def start(self) -> None:
        """启动交互式引导主循环"""
        self.console.print(
            "\n[bold cyan]🚀 DefineX 交互式配置引导[/bold cyan]\n"
            "[dim]使用此菜单配置插件开发环境[/dim]\n"
        )

        while True:
            try:
                self.ui.show_header("DefineX 配置向导")

                # 显示主菜单
                menu = self.ui.menus.render_main_menu()
                self.console.print(menu)

                # 获取用户选择
                choice = self.ui.forms.prompt_choice(
                    ["1", "2", "3", "0"],
                    default="0"
                )
                # 处理选择
                if choice == "1":
                    self.config_handler.configure_push(interactive=True)
                elif choice == "2":
                    self._handle_project_config()
                elif choice == "3":
                    self._handle_show_status()
                elif choice == "0":
                    self._handle_exit()
                    break

                self.ui.show_footer()

            except KeyboardInterrupt:
                self.console.print("\n[yellow]👋 操作已取消[/yellow]")
                break
            except Exception as e:
                self.console.print(f"\n[red]❌ 发生错误: {e}[/red]")
                self.ui.show_footer()

    def menu_guide(self, root_path: Path) -> None:
        """
        菜单引导入口

        Args:
            root_path: 项目根目录
        """
        self.root_path = root_path
        self.start()

    def _handle_project_config(self) -> None:
        """处理项目配置菜单"""
        while True:
            result = self.project_handler.show_menu()
            if result is None:  # 用户选择返回
                break
            self.ui.show_footer()

    def _handle_show_status(self) -> None:
        """处理显示状态菜单"""
        self.status_handler.show_full_status()
        self.ui.show_footer()

    def _handle_exit(self) -> None:
        """处理退出"""
        self.console.print("\n[green]👋 感谢使用 DefineX！[/green]")
