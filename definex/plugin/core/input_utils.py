"""
DefineX 改进的输入处理器
支持历史记录、更好的删除字符处理和自动补全
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Callable, Any, Dict

from rich.console import Console

try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False

try:
    from prompt_toolkit import PromptSession, HTML
    from prompt_toolkit.history import FileHistory, InMemoryHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import WordCompleter
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False


class InputHistory:
    """
    输入历史管理器
    """

    def __init__(self, history_file: Optional[str] = None):
        """
        初始化历史管理器

        Args:
            history_file: 历史文件路径，如果为 None 则使用内存历史
        """
        self.history_file = history_file
        self.history: List[str] = []

        if history_file and os.path.exists(history_file):
            self._load_history()

    def _load_history(self) -> None:
        """从文件加载历史"""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                self.history = [line.strip() for line in f if line.strip()]
        except Exception:
            self.history = []

    def _save_history(self) -> None:
        """保存历史到文件"""
        if not self.history_file:
            return

        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                for item in self.history[-1000:]:  # 最多保存1000条
                    f.write(item + '\n')
        except Exception:
            pass

    def add(self, text: str) -> None:
        """
        添加历史记录

        Args:
            text: 要添加的文本
        """
        if text and text.strip():
            # 避免重复添加相同的命令
            if self.history and self.history[-1] == text:
                return

            self.history.append(text)
            self._save_history()

    def get_all(self) -> List[str]:
        """
        获取所有历史记录

        Returns:
            历史记录列表
        """
        return self.history.copy()

    def search(self, keyword: str) -> List[str]:
        """
        搜索历史记录

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的历史记录
        """
        return [item for item in self.history if keyword.lower() in item.lower()]

    def clear(self) -> None:
        """清空历史记录"""
        self.history.clear()
        if self.history_file and os.path.exists(self.history_file):
            os.remove(self.history_file)


class SmartInput:
    """
    智能输入处理器
    """

    def __init__(self, console: Console, history_file: Optional[str] = None):
        """
        初始化输入处理器

        Args:
            console: Rich Console 实例
            history_file: 历史文件路径
        """
        self.console = console
        self.history = InputHistory(history_file)
        self.prompt_session = None

        # 初始化 prompt_toolkit（如果可用）
        if PROMPT_TOOLKIT_AVAILABLE:
            self._init_prompt_toolkit()
        elif READLINE_AVAILABLE:
            self._init_readline()

    def _init_prompt_toolkit(self) -> None:
        """初始化 prompt_toolkit"""
        try:
            # 创建历史对象
            if self.history.history_file:
                history = FileHistory(self.history.history_file)
            else:
                history = InMemoryHistory()

            # 创建 PromptSession
            self.prompt_session = PromptSession(
                history=history,
                enable_history_search=True,
                complete_while_typing=True,
            )
        except Exception as e:
            self.console.print(f"[yellow]⚠️ 初始化 prompt_toolkit 失败: {e}[/yellow]")
            self.prompt_session = None

    def _init_readline(self) -> None:
        """初始化 readline"""
        try:
            # 设置历史文件
            if self.history.history_file:
                readline.read_history_file(self.history.history_file)

            # 配置 readline
            readline.set_history_length(1000)
            readline.parse_and_bind('tab: complete')
            readline.parse_and_bind('set editing-mode emacs')

            # 设置自动补全
            readline.set_completer(self._readline_completer)
            readline.set_completer_delims(' \t\n`~!@#$%^&*()-=+[{]}\\|;:\'",<>/?')
        except Exception as e:
            self.console.print(f"[yellow]⚠️ 初始化 readline 失败: {e}[/yellow]")

    def _readline_completer(self, text: str, state: int) -> Optional[str]:
        """readline 自动补全函数"""
        # 这里可以添加自定义的自动补全逻辑
        return None

    def prompt(
        self,
        message: str = "",
        default: str = "",
        completer: Optional[Any] = None,
        validator: Optional[Callable[[str], bool]] = None,
        password: bool = False
    ) -> str:
        """
        智能提示输入

        Args:
            message: 提示消息
            default: 默认值
            completer: 自动补全器（仅 prompt_toolkit）
            validator: 输入验证函数
            password: 是否密码输入

        Returns:
            用户输入
        """
        # 使用 prompt_toolkit（如果可用）
        if PROMPT_TOOLKIT_AVAILABLE and self.prompt_session:
            return self._prompt_with_prompt_toolkit(message, default, completer, validator, password)

        # 使用 readline（如果可用）
        elif READLINE_AVAILABLE:
            return self._prompt_with_readline(message, default, password)

        # 使用简单的 input
        else:
            return self._prompt_simple(message, default, password)

    def _prompt_with_prompt_toolkit(
        self,
        message: str,
        default: str,
        completer: Optional[Any],
        validator: Optional[Callable[[str], bool]],
        password: bool
    ) -> str:
        """使用 prompt_toolkit 提示输入"""
        try:
            # 准备提示文本
            prompt_text = HTML(f'<ansicyan>{message}</ansicyan> ') if message else ""

            # 配置会话
            session_kwargs = {}
            if completer:
                session_kwargs['completer'] = completer
            if validator:
                session_kwargs['validator'] = validator

            # 获取输入
            result = self.prompt_session.prompt(
                prompt_text,
                default=default,
                is_password=password,
                **session_kwargs
            )

            # 添加到历史
            if result and result.strip():
                self.history.add(result)

            return result
        except KeyboardInterrupt:
            raise
        except Exception as e:
            self.console.print(f"[red]输入错误: {e}[/red]")
            return default

    def _prompt_with_readline(self, message: str, default: str, password: bool) -> str:
        """使用 readline 提示输入"""
        try:
            # 显示提示
            if message:
                self.console.print(f"[cyan]{message}[/cyan] ", end="")

            # 获取输入
            if password:
                import getpass
                result = getpass.getpass("")
            else:
                result = input()

            # 保存历史
            if result and result.strip():
                self.history.add(result)
                if self.history.history_file:
                    readline.write_history_file(self.history.history_file)

            return result or default
        except KeyboardInterrupt:
            raise
        except EOFError:
            return ""
        except Exception as e:
            self.console.print(f"[red]输入错误: {e}[/red]")
            return default

    def _prompt_simple(self, message: str, default: str, password: bool) -> str:
        """使用简单的 input 提示输入"""
        try:
            # 显示提示
            if message:
                self.console.print(f"[cyan]{message}[/cyan] ", end="")

            # 获取输入
            if password:
                import getpass
                result = getpass.getpass("")
            else:
                result = input()

            # 添加到历史
            if result and result.strip():
                self.history.add(result)

            return result or default
        except KeyboardInterrupt:
            raise
        except EOFError:
            return ""
        except Exception as e:
            self.console.print(f"[red]输入错误: {e}[/red]")
            return default

    def prompt_choice(
        self,
        message: str,
        choices: List[str],
        default: Optional[str] = None
    ) -> str:
        """
        提示选择

        Args:
            message: 提示消息
            choices: 可选值列表
            default: 默认值

        Returns:
            用户选择
        """
        # 显示选项
        self.console.print(f"[cyan]{message}[/cyan]")
        for i, choice in enumerate(choices, 1):
            self.console.print(f"  [{i}] {choice}")

        # 获取选择
        while True:
            try:
                selection = self.prompt(f"请选择 (1-{len(choices)})", default=str(default) if default else "")

                if not selection:
                    if default:
                        return default
                    continue

                # 检查是否是数字选择
                if selection.isdigit():
                    idx = int(selection) - 1
                    if 0 <= idx < len(choices):
                        return choices[idx]

                # 检查是否是直接输入选项
                if selection in choices:
                    return selection

                self.console.print("[red]❌ 无效选择，请重试[/red]")
            except KeyboardInterrupt:
                raise

    def prompt_confirm(self, message: str, default: bool = False) -> bool:
        """
        提示确认

        Args:
            message: 提示消息
            default: 默认值

        Returns:
            True 或 False
        """
        default_text = "Y/n" if default else "y/N"
        prompt_text = f"{message} [{default_text}]"

        while True:
            try:
                response = self.prompt(prompt_text, default="Y" if default else "N").strip().lower()

                if not response:
                    return default
                elif response in ['y', 'yes', '是']:
                    return True
                elif response in ['n', 'no', '否']:
                    return False
                else:
                    self.console.print("[red]❌ 请输入 y/n 或 是/否[/red]")
            except KeyboardInterrupt:
                raise


# 工具函数
def create_input_handler(
    console: Console,
    project_path: Optional[str] = None,
    use_prompt_toolkit: bool = True
) -> SmartInput:
    """
    创建输入处理器

    Args:
        console: Console 实例
        project_path: 项目路径，用于确定历史文件位置
        use_prompt_toolkit: 是否尝试使用 prompt_toolkit

    Returns:
        SmartInput 实例
    """
    # 确定历史文件路径
    history_file = None
    if project_path:
        history_dir = Path(project_path) / ".definex"
        history_dir.mkdir(exist_ok=True)
        history_file = str(history_dir / "input_history.txt")

    # 如果不使用 prompt_toolkit 或不可用，则禁用
    global PROMPT_TOOLKIT_AVAILABLE
    if not use_prompt_toolkit:
        PROMPT_TOOLKIT_AVAILABLE = False

    return SmartInput(console, history_file)


def get_json_input(console: Console, prompt_text: str = "输入 JSON:") -> Optional[Dict]:
    """
    获取 JSON 输入

    Args:
        console: Console 实例
        prompt_text: 提示文本

    Returns:
        JSON 字典或 None
    """
    input_handler = create_input_handler(console)

    while True:
        try:
            json_str = input_handler.prompt(prompt_text)

            if not json_str:
                return None

            # 尝试解析 JSON
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            console.print(f"[red]❌ JSON 解析错误: {e}[/red]")
            console.print("[yellow]请重新输入有效的 JSON[/yellow]")
        except KeyboardInterrupt:
            return None


# 导出常用实例
def get_default_input_handler() -> SmartInput:
    """获取默认输入处理器"""
    from .console_utils import console
    return create_input_handler(console)
