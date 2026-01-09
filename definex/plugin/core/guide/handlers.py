"""
菜单处理器层
负责将用户输入转化为业务操作
"""
from pathlib import Path
from typing import Optional

from definex.exception.exceptions import ConfigException
from definex.plugin.config import (
    ConfigManager, LLMModelConfig, ModelProvider
)
from .views import UIManager


class LLMHandler:
    """LLM 配置处理器"""

    def __init__(self, ui: UIManager, config_mgr: ConfigManager):
        self.ui = ui
        self.config_mgr = config_mgr

    def show_menu(self) -> Optional[str]:
        while True:
            """显示 LLM 菜单并处理用户选择"""
            self.ui.show_header("⚙️ LLM 配置向导")
            # 显示当前配置
            self._show_current_status()
            # 显示菜单
            menu = self.ui.menus.render_llm_menu()
            self.ui.console.print(menu)
            choice = self.ui.forms.prompt_choice(["1", "2", "3", "4", "5", "0"], default="0")
            if choice == "1":
                return self.add_model()
            elif choice == "2":
                return self.switch_model()
            elif choice == "3":
                return self.remove_model()
            elif choice == "4":
                return self.show_all_models()
            elif choice == "5":
                return self.validate_llm_config()
            elif choice == "0":
                self._handle_llm_config_exit()
                break

    def _show_current_status(self) -> None:
        """显示当前 LLM 配置状态"""
        current = self.config_mgr.get_current_llm_config()
        if current:
            self.ui.console.print(f"[bold cyan]当前模型:[/bold cyan] [green]{current.get('model')}[/green]")
        else:
            self.ui.status.show_warning("未配置任何 LLM 模型")

    def add_model(self) -> Optional[str]:
        """添加新模型"""
        self.ui.show_header("添加 LLM 模型")

        try:
            name = self.ui.forms.prompt_string("模型名称", default="gpt-4")

            # 选择提供商
            providers = [p.value for p in ModelProvider]
            provider_str = self.ui.forms.prompt_choice(providers, default=providers[0])
            provider = ModelProvider(provider_str)

            api_key = self.ui.forms.prompt_string("API Key (必填)", password=True)
            base_url = self.ui.forms.prompt_string("Base URL", default="https://api.deepseek.com")

            temperature = self.ui.forms.prompt_int("温度 (0-2)", default=7) / 10
            max_tokens = self.ui.forms.prompt_int("最大 Token 数", default=2000)

            model_config = LLMModelConfig(
                name=name,
                provider=provider,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens
            )

            self.config_mgr.add_or_update_llm_model(model_config, set_as_current=True)
            self.ui.status.show_success(f"模型 {name} 已添加并设为当前模型")
            return "model_added"
        except Exception as e:
            self.ui.status.show_error(str(e))
            return None

    def switch_model(self) -> Optional[str]:
        """切换当前模型"""
        models = self.config_mgr.get_llm_model_names()

        if not models:
            self.ui.status.show_warning("没有可用的模型")
            return None

        self.ui.console.print("\n[bold]可用模型:[/bold]")
        for i, model in enumerate(models, 1):
            self.ui.console.print(f"{i}. {model}")

        choice = self.ui.forms.prompt_choice([str(i) for i in range(1, len(models) + 1)], default="1")

        try:
            selected_model = models[int(choice) - 1]
            self.config_mgr.set_current_llm_model(selected_model)
            self.ui.status.show_success(f"已切换到模型: {selected_model}")
            return "model_switched"
        except (ValueError, IndexError):
            self.ui.status.show_error("无效的选择")
            return None

    def remove_model(self) -> Optional[str]:
        """删除模型"""
        models = self.config_mgr.get_llm_model_names()

        if not models:
            self.ui.status.show_warning("没有可删除的模型")
            return None

        self.ui.console.print("\n[bold]可用模型:[/bold]")
        for i, model in enumerate(models, 1):
            self.ui.console.print(f"{i}. {model}")

        choice = self.ui.forms.prompt_choice([str(i) for i in range(1, len(models) + 1)], default="1")

        try:
            model_to_remove = models[int(choice) - 1]

            if self.ui.forms.prompt_confirm(f"[red]确认删除模型 '{model_to_remove}'？[/red]", default=False):
                self.config_mgr.remove_llm_model(model_to_remove)
                self.ui.status.show_success(f"模型 {model_to_remove} 已删除")
                return "model_removed"
        except (ValueError, IndexError):
            self.ui.status.show_error("无效的选择")
        return None

    def show_all_models(self) -> Optional[str]:
        """展示所有模型"""
        self.ui.console.print("\n[bold cyan]🤖 LLM 配置:[/bold cyan]")
        models_config = self.config_mgr.get_llm_model()
        table = self.ui.tables.render_models_table(
            models_config.get_all_config(),
            models_config.get_current_config())
        self.ui.console.print(table)

    def validate_llm_config(self):
        self.ui.show_header("🤖 校验所有模型配置:")
        result = self.config_mgr.validate_llm_config()
        if len(result) != 0:
            table = self.ui.tables.render_validate_models_table(result)
            self.ui.console.print(table)
        else:
            self.ui.console.print("\n[green]✅ 所有模型配置校验通过:[/green]")

    def _handle_llm_config_exit(self):
        self.ui.show_footer()

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

        choice = self.ui.forms.prompt_choice(["1", "2", "3", "4", "0"], default="0")

        if choice == "1":
            return self.modify_chat_config()
        elif choice == "2":
            return self.export_config()
        elif choice == "3":
            return self.import_config()
        elif choice == "4":
            return self.reset_config()

        return None

    def _show_current_settings(self) -> None:
        """显示当前设置"""
        chat_config = self.config_mgr.get_chat_config()

        settings = {
            "最大历史长度": chat_config.max_history_length,
            "最大上下文 Token": chat_config.max_context_tokens,
            "启用流式输出": "✅ 是" if chat_config.enable_streaming else "❌ 否",
            "自动保存代码": "✅ 是" if chat_config.auto_save_code else "❌ 否",
        }

        table = self.ui.tables.render_config_table(settings, "当前聊天配置")
        self.ui.console.print(table)

    def modify_chat_config(self) -> Optional[str]:
        """修改聊天配置"""
        self.ui.show_header("修改聊天配置")

        current = self.config_mgr.get_chat_config()

        max_history = self.ui.forms.prompt_int(
            "最大历史记录长度",
            default=current.max_history_length
        )

        max_tokens = self.ui.forms.prompt_int(
            "最大上下文 Token",
            default=current.max_context_tokens
        )

        streaming = self.ui.forms.prompt_confirm(
            "启用流式输出",
            default=current.enable_streaming
        )

        auto_save = self.ui.forms.prompt_confirm(
            "自动保存代码",
            default=current.auto_save_code
        )

        try:
            from definex.plugin.config import ChatConfig
            new_config = ChatConfig(
                max_history_length=max_history,
                max_context_tokens=max_tokens,
                enable_streaming=streaming,
                auto_save_code=auto_save,
                code_output_dir=current.code_output_dir,
                default_filename=current.default_filename
            )
            self.config_mgr.save_chat_config(new_config)
            self.ui.status.show_success("聊天配置已更新")
            return "config_updated"
        except Exception as e:
            self.ui.status.show_error(str(e))
            return None

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

        # LLM 信息
        if "llm" in masked:
            self.show_llm_status(masked)

        # Push 信息
        if "push" in masked:
            self.show_push_status(masked)

        # Chat 信息
        if "chat" in masked:
            self.show_chat_status(masked)

    def show_llm_status(self, masked):
        llm_data = masked.get("llm", {})
        self.ui.console.print("\n[bold cyan]🤖 LLM 配置:[/bold cyan]")
        current_model = llm_data.get("current_model", None)
        if "models" in llm_data:
            table = self.ui.tables.render_models_table(llm_data["models"], current_model)
            self.ui.console.print(table)

    def show_push_status(self, masked):
        push_data = masked.get("push", {})
        self.ui.console.print("\n[bold cyan]🚀 发布配置:[/bold cyan]")
        push_table_data = {
            "默认环境": push_data.get("default", "未设置"),
            "环境数": str(len(push_data.get("environments", {})))
        }
        table = self.ui.tables.render_config_table(push_table_data)
        self.ui.console.print(table)

    def show_chat_status(self, masked):
        chat_data = masked.get("chat", {})
        self.ui.console.print("\n[bold cyan]💬 聊天配置:[/bold cyan]")
        chat_table_data = {
            "最大历史": chat_data.get("max_history_length", 10),
            "最大 Token": chat_data.get("max_context_tokens", 4000),
            "流式输出": "✅ 是" if chat_data.get("enable_streaming") else "❌ 否"
        }
        table = self.ui.tables.render_config_table(chat_table_data)
        self.ui.console.print(table)