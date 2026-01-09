"""
统一的配置处理器

消除 dfx plugin config 和 dfx plugin guide 中的冗余配置逻辑
提供统一的配置接口，支持命令行和交互式两种方式
"""

from typing import Dict, Any, Optional

from rich.console import Console

from definex.core import LLMModelConfig, ModelProvider
from definex.plugin.config.manager import ConfigManager
from definex.plugin.config.models import PushEnvironment
from definex.plugin.core.guide.handlers import PushHandler, LLMHandler
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

    # ===== LLM 配置 =====

    def configure_llm(self,
                     model: Optional[str] = None,
                     api_key: Optional[str] = None,
                     base_url: Optional[str] = None,
                     provider: Optional[str] = None,
                     interactive: bool = False) -> bool:
        """
        配置LLM模型（统一方法）

        Args:
            model: 模型名称
            api_key: API密钥
            base_url: 基础URL
            provider: 提供商
            interactive: 是否交互式模式
        """
        self.show_config_status("llm")
        if interactive:
            return self._configure_llm_interactive()
        else:
            return self._configure_llm_cli(model, api_key, base_url, provider)

    def _configure_llm_cli(self,
                          model: Optional[str],
                          api_key: Optional[str],
                          base_url: Optional[str],
                          provider: Optional[str]) -> bool:
        """命令行模式配置LLM"""
        try:
            model_name = model or "default-model"
            provider_str = provider or "deepseek"

            try:
                provider_enum = ModelProvider(provider_str.lower())
            except ValueError:
                provider_enum = ModelProvider.CUSTOM

            model_config = LLMModelConfig(
                name=model_name,
                provider=provider_enum,
                api_key=api_key or "",
                base_url=base_url or "",
                api_version="",
                temperature=0.7,
                max_tokens=2000,
                timeout=60,
                enabled=True,
                description=f"CLI configured model: {model_name}"
            )

            self.config_mgr.add_or_update_llm_model(model_config, set_as_current=True)
            self.console.print(f"[green]✅ LLM配置已更新: {model_name}[/green]")
            return True

        except Exception as e:
            self.console.print(f"[red]❌ LLM配置失败: {e}[/red]")
            return False

    def _configure_llm_interactive(self):
        """交互式模式配置LLM"""

        # 使用现有的LLMHandler
        ui = UIManager(self.console)
        handler = LLMHandler(ui, self.config_mgr)
        try:
            handler.show_menu()
            ui.console.print("[green]✅ LLM配置完成[/green]")
        except Exception as e:
            ui.console.print(f"[red]❌ 交互式配置失败: {e}[/red]")
            return False

    # ===== Push 配置 =====

    def configure_push(self,
                      env: Optional[str] = None,
                      url: Optional[str] = None,
                      token: Optional[str] = None,
                      default: Optional[str] = None,
                      interactive: bool = False):
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
        """命令行模式配置Push"""
        try:
            env_name = env or "default"

            # 获取当前配置
            push_config = self.config_mgr.get_push_config()

            # 更新环境配置
            push_config.environments[env_name] = PushEnvironment(
                name=env_name,
                url=url or "",
                token=token or "",
                description=f"CLI configured environment: {env_name}",
                timeout=30,
                enabled=True
            )

            # 设置默认环境
            if default:
                push_config.default_environment = env_name

            # 保存配置
            self.config_mgr.save_push_config(push_config)

            self.console.print(f"[green]✅ 发布环境配置已更新: {env_name}[/green]")
            if default:
                self.console.print(f"[cyan]📌 已设为默认环境[/cyan]")
            return True

        except Exception as e:
            self.console.print(f"[red]❌ 发布环境配置失败: {e}[/red]")
            return False

    def _configure_push_interactive(self):
        """交互式模式配置Push"""

        # 使用现有的PushHandler
        ui = UIManager(self.console)
        handler = PushHandler(ui, self.config_mgr)
        try:
            handler.show_menu()
            self.console.print("[green]✅ 发布环境配置完成[/green]")
        except Exception as e:
            self.console.print(f"[red]❌ 交互式配置失败: {e}[/red]")
            return False

    # ===== Chat 配置 =====

    def configure_chat(self, data: Dict[str, Any], interactive: bool = False) -> bool:
        """
        配置Chat（统一方法）

        Args:
            data: 配置数据
            interactive: 是否交互式模式

        Returns:
            bool: 配置是否成功
        """
        if interactive:
            # Chat配置目前只有命令行模式
            self.console.print("[yellow]⚠️ Chat配置暂不支持交互式模式[/yellow]")
            return self._configure_chat_cli(data)
        else:
            return self._configure_chat_cli(data)

    def _configure_chat_cli(self, data: Dict[str, Any]) -> bool:
        """命令行模式配置Chat"""
        try:
            from definex.plugin.config.models import ChatConfig
            chat_config = ChatConfig.from_dict(data)
            self.config_mgr.save_chat_config(chat_config)
            self.console.print("[green]✅ Chat配置已更新[/green]")
            return True
        except Exception as e:
            self.console.print(f"[red]❌ Chat配置失败: {e}[/red]")
            return False

    # ===== 通用配置方法 =====

    def show_config_status(self, section: Optional[str] = None) -> None:
        """
        显示配置状态

        Args:
            section: 配置分区（llm/push/chat），None表示显示所有
        """
        self.console.print("[bold cyan]📋 配置状态[/bold cyan]")
        self.console.print("-" * 40)

        if section is None or section == "llm":
            self._show_llm_status()

        if section is None or section == "push":
            self._show_push_status()

        if section is None or section == "chat":
            self._show_chat_status()

    def _show_llm_status(self) -> None:
        """显示LLM配置状态"""
        current = self.config_mgr.get_current_llm_config()
        models = self.config_mgr.get_llm_model_names()

        self.console.print("[bold]🤖 LLM配置:[/bold]")
        if current:
            self.console.print(f"  当前模型: [green]{current.get('model')}[/green]")
            self.console.print(f"  提供商: [cyan]{current.get('provider')}[/cyan]")
            if current.get('base_url'):
                self.console.print(f"  基础URL: [dim]{current.get('base_url')}[/dim]")
        else:
            self.console.print("  当前模型: [yellow]未配置[/yellow]")

        if models:
            self.console.print(f"  可用模型: {', '.join(models)}")
        else:
            self.console.print("  可用模型: [yellow]无[/yellow]")
        self.console.print("")

    def _show_push_status(self) -> None:
        """显示Push配置状态"""
        push_config = self.config_mgr.get_push_config()

        self.console.print("[bold]🚀 发布配置:[/bold]")
        if push_config.default_environment:
            self.console.print(f"  默认环境: [magenta]{push_config.default_environment}[/magenta]")
        else:
            self.console.print("  默认环境: [yellow]未设置[/yellow]")

        if push_config.environments:
            self.console.print(f"  环境数量: {len(push_config.environments)}")
            for env_name, env in push_config.environments.items():
                status = "✅" if env.enabled else "❌"
                self.console.print(f"  {status} {env_name}: {env.url}")
        else:
            self.console.print("  环境数量: [yellow]0[/yellow]")
        self.console.print("")

    def _show_chat_status(self) -> None:
        """显示Chat配置状态"""
        try:
            chat_config = self.config_mgr.get_chat_config()
            self.console.print("[bold]💬 Chat配置:[/bold]")
            self.console.print(f"  系统提示: [dim]{chat_config.system_prompt[:50]}...[/dim]" if chat_config.system_prompt else "  系统提示: [yellow]未设置[/yellow]")
            self.console.print(f"  温度: {chat_config.temperature}")
            self.console.print("")
        except:
            self.console.print("[bold]💬 Chat配置:[/bold]")
            self.console.print("  [yellow]未配置[/yellow]")
            self.console.print("")


# 工厂函数
def create_config_handler(console: Console, config_mgr: ConfigManager) -> UnifiedConfigHandler:
    """创建统一的配置处理器实例"""
    return UnifiedConfigHandler(console, config_mgr)
