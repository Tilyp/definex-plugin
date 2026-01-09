"""
聊天命令处理器
"""
from typing import Dict, List, Any, Callable

from rich.console import Console


class CommandHandler:
    """命令处理器"""

    def __init__(self, console: Console):
        self.console = console
        self.commands: Dict[str, Dict[str, Any]] = {}

    def register_command(self, name: str, description: str, handler: Callable,
                         aliases: List[str] = None, requires_args: bool = False):
        """注册新命令"""
        self.commands[name] = {
            "handler": handler,
            "description": description,
            "aliases": aliases or [],
            "requires_args": requires_args
        }
        # 注册别名
        if aliases:
            for alias in aliases:
                self.commands[alias] = self.commands[name]

    def is_command(self, text: str) -> bool:
        """判断文本是否是命令"""
        if not text:
            return False
        # 检查是否是已知命令
        first_word = text.strip().split()[0].lower()
        return first_word in self.commands

    def execute_command(self, text: str, context: Dict[str, Any]) -> Any:
        """执行命令"""
        if not self.is_command(text):
            return None
        parts = text.strip().split()
        command_name = parts[0].lower()
        if command_name not in self.commands:
            self.console.print(f"[red]❌ 未知命令: {command_name}[/red]")
            return None
        command = self.commands[command_name]
        args = parts[1:] if len(parts) > 1 else []
        try:
            return command["handler"](args, context)
        except Exception as e:
            self.console.print(f"[red]❌ 执行命令失败: {e}[/red]")
            return None

    def get_command_help(self) -> str:
        """获取命令帮助文本"""
        help_text = []
        for name, cmd_info in self.commands.items():
            # 只显示主命令，不显示别名
            if name in cmd_info.get("aliases", []):
                continue
            aliases = cmd_info.get("aliases", [])
            aliases_str = f" (别名: {', '.join(aliases)})" if aliases else ""
            help_text.append(f"• [cyan]{name:10}[/cyan] - {cmd_info['description']}{aliases_str}")
        return "\n".join(help_text)
