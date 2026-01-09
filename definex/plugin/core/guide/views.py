"""
交互式菜单的 UI 视图层
负责所有的菜单渲染和用户交互
"""
from typing import List, Dict, Any, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table


class MenuRenderer:
    """菜单渲染器"""

    def __init__(self, console: Console):
        self.console = console

    def render_main_menu(self, project_name: str = None) -> Table:
        """渲染主菜单"""
        menu = Table(show_header=False, box=None, padding=(0, 2))

        menu.add_row("[1] ⚙️ 配置 LLM (AI 代码辅助)", "[dim]选择或配置 AI 模型[/dim]")
        menu.add_row("[2] 🚀 配置发布环境 (Push)", "[dim]配置发布目标和凭证[/dim]")
        menu.add_row("[3] 🛠️管理项目配置", "[dim]调整聊天和代码生成设置[/dim]")
        menu.add_row("[4] 🤖 开启 AI 结对编程", "[dim]与 AI 共同编写代码[/dim]")
        menu.add_row("[5] 📋 查看全局配置详情", "[dim]查看所有配置[/dim]")
        menu.add_row("[0] 🚪 退出引导", "[dim]回到命令行[/dim]")

        return menu

    def render_llm_menu(self) -> Table:
        """渲染 LLM 配置菜单"""
        menu = Table(show_header=False, box=None, padding=(0, 2))

        menu.add_row("[1] 添加新模型", "[dim]配置新的 LLM 提供商[/dim]")
        menu.add_row("[2] 切换当前模型", "[dim]选择要使用的模型[/dim]")
        menu.add_row("[3] 删除模型", "[dim]移除已配置的模型[/dim]")
        menu.add_row("[4] 查看所有模型", "[dim]查看所有模型[/dim]")
        menu.add_row("[5] 校验所有模型配置", "[dim]校验所有模型配置[/dim]")
        menu.add_row("[0] 返回", "[dim]回到主菜单[/dim]")

        return menu

    def render_push_menu(self) -> Table:
        """渲染 Push 配置菜单"""
        menu = Table(show_header=False, box=None, padding=(0, 2))

        menu.add_row("[1] 添加/更新环境", "[dim]配置新的发布环境[/dim]")
        menu.add_row("[2] 设置默认环境", "[dim]选择默认发布目标[/dim]")
        menu.add_row("[3] 删除环境", "[dim]移除发布环境[/dim]")
        menu.add_row("[0] 返回", "[dim]回到主菜单[/dim]")

        return menu

    def render_project_menu(self) -> Table:
        """渲染项目配置菜单"""
        menu = Table(show_header=False, box=None, padding=(0, 2))

        menu.add_row("[1] 修改聊天配置", "[dim]调整聊天参数[/dim]")
        menu.add_row("[2] 导出配置", "[dim]备份当前配置[/dim]")
        menu.add_row("[3] 导入配置", "[dim]恢复已保存的配置[/dim]")
        menu.add_row("[4] 重置配置", "[dim]恢复为默认值[/dim]")
        menu.add_row("[0] 返回", "[dim]回到主菜单[/dim]")

        return menu


class TableRenderer:
    """表格渲染器"""

    def __init__(self, console: Console):
        self.console = console

    def render_models_table(self, models: Dict[str, Any], current_model: Optional[str] = None) -> Table:
        """渲染 LLM 模型表格"""
        table = Table(title="已配置的 LLM 模型", show_header=True, header_style="bold cyan")
        table.add_column("提供商", style="yellow")
        table.add_column("模型名称", style="green")
        table.add_column("Base URL", style="blue")
        table.add_column("状态", style="cyan")
        table.add_column("当前", style="magenta")

        for name, model in models.items():
            is_current = "✅" if name == current_model else ""
            status = "✅ 启用" if model.get("enabled", True) else "❌ 禁用"
            provider = model.get("provider", "unknown")
            base_url = model.get("base_url", "unknown")
            table.add_row(provider, name, base_url, status, is_current)
        return table

    def render_environments_table(self, environments: Dict[str, Any], default_env: Optional[str] = None) -> Table:
        """渲染发布环境表格"""
        table = Table(title="发布环境配置", show_header=True, header_style="bold magenta")
        table.add_column("环境名称", style="green")
        table.add_column("URL", style="cyan")
        table.add_column("默认", style="magenta")

        for name, env in environments.items():
            is_default = "✅" if name == default_env else ""
            url = env.get("url", "未设置")
            table.add_row(name, url, is_default)

        return table

    def render_validate_models_table(self, result: Dict[str, List[str]]) -> Table:
        """渲染发布环境表格"""
        table = Table(title="模型配置校验结果", show_header=True, header_style="bold magenta")
        table.add_column("模型名称", style="green")
        table.add_column("结果", style="cyan")
        for name, errors in result.items():
            errors_str = ";".join(errors)
            table.add_row(name, errors_str)
        return table

    def render_config_table(self, config_data: Dict[str, Any], title: str = "配置信息") -> Table:
        """渲染通用配置表格"""
        table = Table(title=title, show_header=False, box=None)
        table.add_column("配置项", style="cyan")
        table.add_column("当前值", style="green")

        for key, value in config_data.items():
            table.add_row(key, str(value))

        return table


class FormRenderer:
    """表单渲染器"""

    def __init__(self, console: Console):
        self.console = console

    def prompt_string(self, prompt_text: str, default: str = "", password: bool = False) -> str:
        """提示输入字符串"""
        return Prompt.ask(prompt_text, default=default, password=password)

    def prompt_int(self, prompt_text: str, default: int = 0) -> int:
        """提示输入整数"""
        try:
            value = Prompt.ask(prompt_text, default=str(default))
            return int(value)
        except ValueError:
            self.console.print("[red]❌ 请输入有效的整数[/red]")
            return default

    def prompt_choice(self, options: List[str], default: Optional[str] = None) -> str:
        """提示选择选项"""
        return Prompt.ask("请选择", choices=options, default=default)

    def prompt_confirm(self, prompt_text: str, default: bool = False) -> bool:
        """提示确认"""
        return Confirm.ask(prompt_text, default=default)

    def render_form(self, fields: Dict[str, Tuple[str, bool]]) -> Dict[str, str]:
        """
        渲染表单并收集输入

        Args:
            fields: 字段定义 {"field_name": ("提示文本", is_password)}

        Returns:
            输入的数据字典
        """
        result = {}
        for field_name, (prompt_text, is_password) in fields.items():
            result[field_name] = self.prompt_string(prompt_text, password=is_password)
        return result


class StatusRenderer:
    """状态显示器"""

    def __init__(self, console: Console):
        self.console = console

    def show_success(self, message: str) -> None:
        """显示成功消息"""
        self.console.print(f"[bold green]✅ {message}[/bold green]")

    def show_error(self, message: str) -> None:
        """显示错误消息"""
        self.console.print(f"[bold red]❌ {message}[/bold red]")

    def show_warning(self, message: str) -> None:
        """显示警告消息"""
        self.console.print(f"[bold yellow]⚠️ {message}[/bold yellow]")

    def show_info(self, message: str) -> None:
        """显示信息消息"""
        self.console.print(f"[bold cyan]ℹ️ {message}[/bold cyan]")

    def show_panel(self, content: str, title: str = "", style: str = "cyan") -> None:
        """显示面板"""
        panel = Panel(content, title=title, border_style=style)
        self.console.print(panel)


class UIManager:
    """统一的 UI 管理器"""

    def __init__(self, console: Console):
        self.console = console
        self.menus = MenuRenderer(console)
        self.tables = TableRenderer(console)
        self.forms = FormRenderer(console)
        self.status = StatusRenderer(console)

    def show_header(self, title: str) -> None:
        """显示标题"""
        self.console.print(f"\n[bold cyan]{title}[/bold cyan]")
        self.console.print("-" * 50)

    def show_footer(self) -> None:
        """显示页脚"""
        self.console.print()
