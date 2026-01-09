"""
代码写入器，负责将生成的代码保存到文件
"""
import shutil
from pathlib import Path
from typing import Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.status import Status
from rich.syntax import Syntax
from rich.table import Table

from definex.plugin.chat.test_file_manager import TestFileManager


class CodeWriter:
    """代码写入器"""

    def __init__(self, console: Console):
        self.console = console
        self.backup_dir = "backups"
        self.test_file_manager = TestFileManager(console)

    def write_code(self, root_path: Path, code: str, filename: str = "main.py",
                   backup: bool = True, preview: bool = True) -> Tuple[bool, Optional[str]]:
        """
        将代码写入文件

        Args:
            root_path: 项目根目录
            code: 要写入的代码
            filename: 文件名
            backup: 是否备份原文件
            preview: 是否预览代码

        Returns:
            (success, error_message)
        """
        target_dir = root_path / "tools"
        target_file = target_dir / filename

        try:
            # 确保目录存在
            target_dir.mkdir(parents=True, exist_ok=True)
            # 预览代码
            if preview:
                self._preview_code(code, filename)

            # 备份原文件（如果存在）
            if backup and target_file.exists():
                backup_path = self._create_backup(root_path, target_file)
                self.console.print(f"[dim]📦 已备份原文件到: {backup_path}[/dim]")

            # 确认写入
            if not self._confirm_write(target_file, root_path):
                return False, "用户取消"

            # 写入文件
            with Status("正在保存代码...", console=self.console):
                target_file.write_text(code, encoding="utf-8")

            # 验证写入
            written_content = target_file.read_text(encoding="utf-8")
            if written_content != code:
                self.console.print("[yellow]⚠️  警告: 写入内容与预期不完全一致[/yellow]")

            # 显示成功信息
            self.console.print(f"[bold green]✅ 代码已成功保存到:[/bold green]")
            self.console.print(f"  [cyan]{target_file.relative_to(root_path)}[/cyan]")

            # 显示文件统计
            self._show_file_stats(code, target_file)

            return True, None

        except Exception as e:
            error_msg = f"保存代码失败: {e}"
            self.console.print(f"[red]❌ {error_msg}[/red]")
            return False, error_msg

    def _preview_code(self, code: str, filename: str):
        """预览代码"""
        self.console.print(f"\n[bold]📄 代码预览 ({filename}):[/bold]")

        # 显示代码语法高亮
        syntax = Syntax(code, "python", theme="monokai", line_numbers=True)

        panel = Panel(
            syntax,
            title=f"代码预览 - {filename}",
            border_style="blue"
        )
        self.console.print(panel)

        # 显示代码统计
        lines = code.splitlines()
        non_empty_lines = [line for line in lines if line.strip()]

        self.console.print(f"[dim]行数: {len(lines)} | 非空行: {len(non_empty_lines)} | 字符数: {len(code)}[/dim]")

    def _confirm_write(self, target_file: Path, root_path: Path) -> bool:
        """确认写入文件"""
        relative_path = target_file.relative_to(root_path)

        # 检查是否在交互式环境中
        try:
            import sys
            is_interactive = sys.stdin.isatty() and sys.stdout.isatty()
        except:
            is_interactive = False

        if not is_interactive:
            # 非交互式环境，自动确认
            self.console.print(f"[dim]📝 非交互式环境，自动确认写入: {relative_path}[/dim]")
            return True

        # 交互式环境，询问用户
        if target_file.exists():
            # 文件已存在，需要确认覆盖
            confirm = Confirm.ask(
                f"[bold yellow]⚠️  文件 {relative_path} 已存在，是否覆盖？[/bold yellow]",
                default=False
            )
            return confirm
        else:
            # 新文件，确认创建
            confirm = Confirm.ask(
                f"[bold yellow]创建新文件 {relative_path}？[/bold yellow]",
                default=True
            )
            return confirm


    def _create_backup(self, root_path: Path, original_file: Path) -> Path:
        """创建备份文件"""
        import time
        timestamp = int(time.time())
        backup_path =  root_path / self.backup_dir
        backup_path.mkdir(parents=True, exist_ok=True)
        backup_file = backup_path / f"{original_file.name}.backup.{timestamp}"
        # 复制文件
        shutil.copy2(original_file, backup_file)
        return backup_file

    def _show_file_stats(self, code: str, file_path: Path):
        """显示文件统计信息"""
        lines = code.splitlines()

        # 统计Python元素
        class_count = sum(1 for line in lines if line.strip().startswith("class "))
        func_count = sum(1 for line in lines if line.strip().startswith("def "))
        import_count = sum(1 for line in lines if line.strip().startswith(("import ", "from ")))

        # 统计代码行类型
        code_lines = 0
        comment_lines = 0
        blank_lines = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
            elif stripped.startswith("#"):
                comment_lines += 1
            else:
                code_lines += 1

        # 显示统计表格
        table = Table(title="文件统计", show_header=False, box=None)
        table.add_column("项目", style="cyan")
        table.add_column("数值", style="green")

        table.add_row("总行数", str(len(lines)))
        table.add_row("代码行", str(code_lines))
        table.add_row("注释行", str(comment_lines))
        table.add_row("空行", str(blank_lines))
        table.add_row("", "")  # 空行分隔
        table.add_row("类定义", str(class_count))
        table.add_row("函数定义", str(func_count))
        table.add_row("导入语句", str(import_count))

        self.console.print(table)

    def write_test_file(self, root_path: Path, test_code: str,
                       test_filename: str = "test_generated.py",
                       backup: bool = True, preview: bool = True) -> Tuple[bool, Optional[str]]:
        """
        将测试代码保存到tests/目录

        Args:
            root_path: 项目根目录
            test_code: 测试代码
            test_filename: 测试文件名
            backup: 是否备份原文件
            preview: 是否预览代码

        Returns:
            (success, error_message)
        """
        return self.test_file_manager.save_test_file(
            root_path, test_code, test_filename, backup, preview
        )

    def write_multiple_test_files(self, root_path: Path,
                                test_files: list, backup: bool = True) -> Tuple[bool, list]:
        """
        保存多个测试文件

        Args:
            root_path: 项目根目录
            test_files: 测试文件列表，每个元素为(文件名, 代码)
            backup: 是否备份原文件

        Returns:
            (success, 错误消息列表)
        """
        return self.test_file_manager.save_multiple_test_files(
            root_path, test_files, backup
        )

    def cleanup_test_files(self, root_path: Path,
                          pattern: str = "test_*.py",
                          confirm: bool = True) -> Tuple[bool, list]:
        """
        清理测试文件

        Args:
            root_path: 项目根目录
            pattern: 文件匹配模式
            confirm: 是否确认删除

        Returns:
            (success, 删除的文件列表)
        """
        return self.test_file_manager.cleanup_test_files(
            root_path, pattern, confirm
        )

    def get_test_directory(self, root_path: Path) -> Path:
        """获取测试目录路径"""
        return self.test_file_manager.get_test_directory(root_path)

    def ensure_test_directory(self, root_path: Path) -> Path:
        """确保测试目录存在"""
        return self.test_file_manager.ensure_test_directory(root_path)

    def list_test_files(self, root_path: Path) -> list:
        """列出所有测试文件"""
        return self.test_file_manager.list_test_files(root_path)
