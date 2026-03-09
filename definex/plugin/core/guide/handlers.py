"""
菜单处理器层
负责将用户输入转化为业务操作
"""
from pathlib import Path
from typing import Optional

from definex.exception.exceptions import ConfigException
from definex.plugin.config import ConfigManager
from .views import UIManager




class PushHandler:
    """Push 配置处理器"""

    def __init__(self, ui: UIManager, config_mgr: ConfigManager):
        self.ui = ui
        self.config_mgr = config_mgr

    def show_menu(self) -> Optional[str]:
        while True:
            """显示 Push 菜单"""
            self.ui.show_header("🚀 发布环境配置向导")

            # 显示当前配置
            self._show_current_status()

            # 显示菜单
            menu = self.ui.menus.render_push_menu()
            self.ui.console.print(menu)

            choice = self.ui.forms.prompt_choice(["1", "2", "3", "0"], default="0")

            if choice == "1":
                self.add_environment()
            elif choice == "2":
                self.set_default()
            elif choice == "3":
                self.remove_environment()
            elif choice == "0":
                self.ui.show_footer()
                break

    def _show_current_status(self) -> None:
        """显示当前发布环境状态"""
        push_config = self.config_mgr.get_push_config()
        if push_config.default_environment:
            self.ui.console.print(f"[bold cyan]默认环境:[/bold cyan] [magenta]{push_config.default_environment}[/magenta]")
        else:
            self.ui.status.show_warning("未配置任何发布环境")

    def add_environment(self) -> Optional[str]:
        """添加或更新发布环境"""
        self.ui.show_header("添加/更新发布环境")

        env_name = self.ui.forms.prompt_string("环境名称 (dev/prod)", default="dev")
        url = self.ui.forms.prompt_string("发布地址 (URL)")
        token = self.ui.forms.prompt_string("认证 Token", password=True)
        description = self.ui.forms.prompt_string("环境描述 (可选)", default="")

        try:
            self.config_mgr.set_env_config(
                env_name=env_name,
                url=url,
                token=token,
                description=description
            )
            self.ui.status.show_success(f"环境 '{env_name}' 已配置")
            return "env_added"
        except ConfigException as e:
            self.ui.status.show_error(str(e))
            return None

    def set_default(self) -> Optional[str]:
        """设置默认环境"""
        environments = self.config_mgr.get_environment_names()

        if not environments:
            self.ui.status.show_warning("没有可用的环境")
            return None

        self.ui.console.print("\n[bold]可用环境:[/bold]")
        for i, env in enumerate(environments, 1):
            self.ui.console.print(f"{i}. {env}")

        choice = self.ui.forms.prompt_choice([str(i) for i in range(1, len(environments) + 1)], default="1")

        try:
            selected_env = environments[int(choice) - 1]
            push_config = self.config_mgr.get_push_config()
            push_config.default_environment = selected_env
            self.config_mgr.save_push_config(push_config)
            self.ui.status.show_success(f"已设置默认环境: {selected_env}")
            return "default_set"
        except (ValueError, IndexError):
            self.ui.status.show_error("无效的选择")
            return None

    def remove_environment(self) -> Optional[str]:
        """删除环境"""
        environments = self.config_mgr.get_environment_names()

        if not environments:
            self.ui.status.show_warning("没有可删除的环境")
            return None

        self.ui.console.print("\n[bold]可用环境:[/bold]")
        for i, env in enumerate(environments, 1):
            self.ui.console.print(f"{i}. {env}")

        choice = self.ui.forms.prompt_choice([str(i) for i in range(1, len(environments) + 1)], default="1")

        try:
            env_to_remove = environments[int(choice) - 1]

            if self.ui.forms.prompt_confirm(f"[red]确认删除环境 '{env_to_remove}'？[/red]", default=False):
                self.config_mgr.remove_environment(env_to_remove)
                self.ui.status.show_success(f"环境 {env_to_remove} 已删除")
                return "env_removed"
        except (ValueError, IndexError):
            self.ui.status.show_error("无效的选择")

        return None


class ProjectHandler:
    """项目配置处理器"""

    def __init__(self, ui: UIManager, config_mgr: ConfigManager):
        self.ui = ui
        self.config_mgr = config_mgr

    def show_menu(self) -> Optional[str]:
        """显示项目配置菜单"""
        self.ui.show_header("🛠️ 项目配置管理")

        # 显示当前设置
        self._show_current_settings()

        menu = self.ui.menus.render_project_menu()
        self.ui.console.print(menu)

        choice = self.ui.forms.prompt_choice(["1", "2", "3", "0"], default="0")

        if choice == "1":
            return self.export_config()
        elif choice == "2":
            return self.import_config()
        elif choice == "3":
            return self.reset_config()

        return None

    def _show_current_settings(self) -> None:
        """显示当前设置"""
        # 显示项目配置信息
        self.ui.console.print("[dim]项目配置管理[/dim]")
        self.ui.console.print("")



    def export_config(self) -> Optional[str]:
        """导出配置"""
        self.ui.show_header("导出配置")

        export_path = self.ui.forms.prompt_string(
            "导出文件路径",
            default=str(Path.home() / ".definex" / "config_export.yaml")
        )

        include_secrets = self.ui.forms.prompt_confirm("包含敏感信息", default=False)

        try:
            success = self.config_mgr.export_config(Path(export_path), include_secrets)
            if success:
                self.ui.status.show_success(f"配置已导出到: {export_path}")
                return "exported"
        except Exception as e:
            self.ui.status.show_error(str(e))

        return None

    def import_config(self) -> Optional[str]:
        """导入配置"""
        self.ui.show_header("导入配置")

        import_path = self.ui.forms.prompt_string("导入文件路径")
        merge = self.ui.forms.prompt_confirm("合并现有配置", default=True)

        try:
            if not Path(import_path).exists():
                self.ui.status.show_error(f"文件不存在: {import_path}")
                return None

            success = self.config_mgr.import_config(Path(import_path), merge)
            if success:
                self.ui.status.show_success("配置已导入")
                return "imported"
        except Exception as e:
            self.ui.status.show_error(str(e))

        return None

    def reset_config(self) -> Optional[str]:
        """重置配置"""
        if self.ui.forms.prompt_confirm("[red]⚠️ 确认重置所有配置为默认值？此操作不可撤销![/red]", default=False):
            try:
                self.config_mgr.reset_config()
                self.ui.status.show_success("配置已重置为默认值")
                return "reset"
            except Exception as e:
                self.ui.status.show_error(str(e))

        return None


class StatusHandler:
    """状态显示处理器"""

    def __init__(self, ui: UIManager, config_mgr: ConfigManager):
        self.ui = ui
        self.config_mgr = config_mgr

    def show_full_status(self) -> None:
        """显示完整配置状态"""
        self.ui.show_header("📋 全局配置状态 (已脱敏)")

        masked = self.config_mgr.get_masked_config()

        # Push 信息
        if "push" in masked:
            self.show_push_status(masked)



    def show_push_status(self, masked):
        push_data = masked.get("push", {})
        self.ui.console.print("\n[bold cyan]🚀 发布配置:[/bold cyan]")
        push_table_data = {
            "默认环境": push_data.get("default", "未设置"),
            "环境数": str(len(push_data.get("environments", {})))
        }
        table = self.ui.tables.render_config_table(push_table_data)
        self.ui.console.print(table)
