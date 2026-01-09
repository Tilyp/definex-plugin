"""
DefineX 优化的 Console 工厂
提供更好的输出显示和用户体验
"""

import os
from typing import Optional

from rich.console import Console
from rich.pager import Pager
from rich.panel import Panel
from rich.table import Table


class OptimizedConsole(Console):
    """
    优化的 Console 类，提供更好的显示体验
    """

    def __init__(self, **kwargs):
        # 设置默认优化参数
        defaults = {
            "width": min(120, self._get_terminal_width()),
            "height": min(40, self._get_terminal_height()),
            "soft_wrap": True,
            "highlight": True,
            "markup": True,
            "emoji": True,
            "force_terminal": True,
            "color_system": "auto",
        }

        # 更新用户自定义参数
        defaults.update(kwargs)
        super().__init__(**defaults)

    @staticmethod
    def _get_terminal_width() -> int:
        """获取终端宽度"""
        try:
            return os.get_terminal_size().columns
        except (OSError, AttributeError):
            return 80

    @staticmethod
    def _get_terminal_height() -> int:
        """获取终端高度"""
        try:
            return os.get_terminal_size().lines
        except (OSError, AttributeError):
            return 24

    def print_long_text(self, text: str, max_lines: int = 20, title: str = "") -> None:
        """
        打印长文本，自动分页或截断

        Args:
            text: 要打印的文本
            max_lines: 最大显示行数
            title: 面板标题
        """
        lines = text.split('\n')

        if len(lines) <= max_lines:
            # 文本不长，直接显示
            if title:
                self.print(Panel(text, title=title, border_style="cyan"))
            else:
                self.print(text)
            return

        # 文本过长，显示前 N 行并提供提示
        preview = '\n'.join(lines[:max_lines])
        remaining = len(lines) - max_lines

        if title:
            panel_content = f"{preview}\n\n[dim yellow]... 还有 {remaining} 行未显示，按 Enter 查看全部[/dim yellow]"
            self.print(Panel(panel_content, title=title, border_style="yellow"))
        else:
            self.print(f"{preview}\n[dim yellow]... 还有 {remaining} 行未显示[/dim yellow]")

        # 询问是否继续查看
        try:
            import sys
            response = input("\n按 Enter 继续查看，或输入 q 退出: ")
            if response.lower() != 'q':
                # 使用分页器显示全部内容
                self.print_with_pager(text, title)
        except KeyboardInterrupt:
            pass

    def create_smart_table(self, title: str = "", **kwargs) -> Table:
        """
        创建智能表格，自动调整列宽

        Args:
            title: 表格标题
            **kwargs: 传递给 Table 的额外参数
        """
        defaults = {
            "show_header": True,
            "header_style": "bold cyan",
            "border_style": "blue",
            "title_style": "bold magenta",
            "expand": False,
            "show_lines": False,
            "row_styles": ["", "dim"],
        }

        defaults.update(kwargs)
        table = Table(**defaults)

        if title:
            table.title = title

        return table

    def print_with_pager(self, content: str, title: str = "") -> None:
        """
        使用分页器显示长内容

        Args:
            content: 要显示的内容
            title: 分页器标题
        """
        with Pager() as pager:
            if title:
                pager.show(f"# {title}\n\n{content}")
            else:
                pager.show(content)


class ConsoleFactory:
    """
    Console 工厂，提供统一的 Console 实例
    """

    _instance: Optional[OptimizedConsole] = None

    @classmethod
    def get_console(cls, **kwargs) -> OptimizedConsole:
        """
        获取优化的 Console 实例（单例模式）

        Args:
            **kwargs: 传递给 Console 的额外参数

        Returns:
            OptimizedConsole 实例
        """
        if cls._instance is None:
            cls._instance = OptimizedConsole(**kwargs)
        return cls._instance

    @classmethod
    def create_console(cls, **kwargs) -> OptimizedConsole:
        """
        创建新的 Console 实例

        Args:
            **kwargs: 传递给 Console 的额外参数

        Returns:
            新的 OptimizedConsole 实例
        """
        return OptimizedConsole(**kwargs)

    @classmethod
    def is_machine_mode(cls) -> bool:
        """
        检查是否处于机器模式（非交互模式）

        Returns:
            True 如果是机器模式，False 如果是交互模式
        """
        # 检查环境变量或命令行参数
        import os
        import sys

        # 检查环境变量
        if os.getenv("DFX_MACHINE_MODE") == "1":
            return True

        # 检查命令行参数
        if "--machine" in sys.argv or "--json" in sys.argv:
            return True

        # 检查是否重定向了输出
        if not sys.stdout.isatty():
            return True

        return False


# 工具函数
def wrap_long_lines(text: str, max_width: int = 80) -> str:
    """
    包装长行文本

    Args:
        text: 输入文本
        max_width: 最大行宽

    Returns:
        包装后的文本
    """
    lines = text.split('\n')
    wrapped_lines = []

    for line in lines:
        if len(line) <= max_width:
            wrapped_lines.append(line)
        else:
            # 智能分词包装
            words = line.split()
            current_line = ""

            for word in words:
                if len(current_line) + len(word) + 1 <= max_width:
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
                else:
                    wrapped_lines.append(current_line)
                    current_line = word

            if current_line:
                wrapped_lines.append(current_line)

    return '\n'.join(wrapped_lines)


def truncate_with_ellipsis(text: str, max_length: int = 100) -> str:
    """
    智能截断文本并添加省略号

    Args:
        text: 输入文本
        max_length: 最大长度

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text

    # 尝试在单词边界处截断
    if max_length > 20:
        truncated = text[:max_length-3]
        # 找到最后一个空格
        last_space = truncated.rfind(' ')
        if last_space > max_length // 2:
            truncated = truncated[:last_space]

        return truncated + "..."
    else:
        return text[:max_length-3] + "..."


# 导出常用实例
console = ConsoleFactory.get_console()
create_console = ConsoleFactory.create_console
