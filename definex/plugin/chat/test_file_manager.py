"""
测试文件管理器 - 管理测试文件的创建和保存位置
确保测试文件保存在项目目录下的tests/目录中，而不是/tmp目录
"""
import shutil
from pathlib import Path
from typing import Optional, Tuple, List

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.status import Status
from rich.syntax import Syntax
from rich.table import Table


class TestFileManager:
    """测试文件管理器"""

    def __init__(self, console: Console):
        self.console = console
        self.test_dir_name = "tests"
        self.backup_dir = "backups"

    def save_test_file(self, root_path: Path, test_code: str,
                      test_filename: str = "test_generated.py",
                      backup: bool = True, preview: bool = True) -> Tuple[bool, Optional[str]]:
        """
        保存测试文件到项目目录下的tests/目录

        Args:
            root_path: 项目根目录
            test_code: 测试代码
            test_filename: 测试文件名
            backup: 是否备份原文件
            preview: 是否预览代码

        Returns:
            (success, error_message)
        """
        # 确保测试文件名以test_开头
        if not test_filename.startswith("test_"):
            test_filename = f"test_{test_filename}"

        # 确保文件扩展名为.py
        if not test_filename.endswith(".py"):
            test_filename = f"{test_filename}.py"

        # 创建测试目录
        test_dir = root_path / self.test_dir_name
        target_file = test_dir / test_filename

        try:
            # 确保目录存在
            test_dir.mkdir(parents=True, exist_ok=True)

            # 预览测试代码
            if preview:
                self._preview_test_code(test_code, test_filename)

            # 备份原文件（如果存在）
            if backup and target_file.exists():
                backup_path = self._create_backup(root_path, target_file)
                self.console.print(f"[dim]📦 已备份原测试文件到: {backup_path}[/dim]")

            # 确认写入
            if not self._confirm_write(target_file, root_path):
                return False, "用户取消"

            # 写入测试文件
            with Status("正在保存测试文件...", console=self.console):
                target_file.write_text(test_code, encoding="utf-8")

            # 验证写入
            written_content = target_file.read_text(encoding="utf-8")
            if written_content != test_code:
                self.console.print("[yellow]⚠️  警告: 写入内容与预期不完全一致[/yellow]")

            # 显示成功信息
            self.console.print(f"[bold green]✅ 测试文件已成功保存到:[/bold green]")
            self.console.print(f"  [cyan]{target_file.relative_to(root_path)}[/cyan]")

            # 显示文件统计
            self._show_test_file_stats(test_code, target_file)

            # 显示测试运行建议
            self._show_test_run_suggestions(root_path)

            return True, None

        except Exception as e:
            error_msg = f"保存测试文件失败: {e}"
            self.console.print(f"[red]❌ {error_msg}[/red]")
            return False, error_msg

    def save_multiple_test_files(self, root_path: Path,
                               test_files: List[Tuple[str, str]],
                               backup: bool = True) -> Tuple[bool, List[str]]:
        """
        保存多个测试文件

        Args:
            root_path: 项目根目录
            test_files: 测试文件列表，每个元素为(文件名, 代码)
            backup: 是否备份原文件

        Returns:
            (success, 错误消息列表)
        """
        errors = []
        success_count = 0

        for test_filename, test_code in test_files:
            success, error = self.save_test_file(
                root_path, test_code, test_filename, backup, preview=False
            )

            if success:
                success_count += 1
            else:
                errors.append(f"{test_filename}: {error}")

        # 显示总结
        total_count = len(test_files)
        self.console.print(f"\n[bold]📊 测试文件保存总结:[/bold]")
        self.console.print(f"  成功: {success_count}/{total_count}")

        if errors:
            self.console.print(f"  失败: {len(errors)}")
            for error in errors:
                self.console.print(f"    • {error}")

        return len(errors) == 0, errors

    def cleanup_test_files(self, root_path: Path,
                          pattern: str = "test_*.py",
                          confirm: bool = True) -> Tuple[bool, List[str]]:
        """
        清理测试文件

        Args:
            root_path: 项目根目录
            pattern: 文件匹配模式
            confirm: 是否确认删除

        Returns:
            (success, 删除的文件列表)
        """
        test_dir = root_path / self.test_dir_name

        if not test_dir.exists():
            self.console.print("[yellow]⚠️  tests目录不存在，无需清理[/yellow]")
            return True, []

        # 查找匹配的文件
        test_files = list(test_dir.glob(pattern))

        if not test_files:
            self.console.print("[yellow]⚠️  没有找到匹配的测试文件[/yellow]")
            return True, []

        # 显示要删除的文件
        self.console.print(f"[bold yellow]⚠️  找到 {len(test_files)} 个匹配的测试文件:[/bold yellow]")
        for test_file in test_files:
            self.console.print(f"  • {test_file.relative_to(root_path)}")

        # 确认删除
        if confirm:
            delete_all = Confirm.ask(
                f"[bold red]确认删除以上 {len(test_files)} 个测试文件？[/bold red]",
                default=False
            )
            if not delete_all:
                self.console.print("[yellow]操作已取消[/yellow]")
                return False, []

        # 删除文件
        deleted_files = []
        for test_file in test_files:
            try:
                test_file.unlink()
                deleted_files.append(str(test_file.relative_to(root_path)))
            except Exception as e:
                self.console.print(f"[red]❌ 删除失败 {test_file.name}: {e}[/red]")

        if deleted_files:
            self.console.print(f"[green]✅ 已删除 {len(deleted_files)} 个测试文件[/green]")

        return True, deleted_files

    def get_test_directory(self, root_path: Path) -> Path:
        """获取测试目录路径"""
        return root_path / self.test_dir_name

    def ensure_test_directory(self, root_path: Path) -> Path:
        """确保测试目录存在"""
        test_dir = self.get_test_directory(root_path)
        test_dir.mkdir(parents=True, exist_ok=True)
        return test_dir

    def list_test_files(self, root_path: Path) -> List[Path]:
        """列出所有测试文件"""
        test_dir = self.get_test_directory(root_path)

        if not test_dir.exists():
            return []

        # 查找所有测试文件
        test_files = []
        for pattern in ["test_*.py", "*_test.py"]:
            test_files.extend(test_dir.glob(pattern))

        # 去重并排序
        test_files = sorted(set(test_files))
        return test_files

    def _preview_test_code(self, test_code: str, test_filename: str):
        """预览测试代码"""
        self.console.print(f"\n[bold]🧪 测试代码预览 ({test_filename}):[/bold]")

        # 显示代码语法高亮
        syntax = Syntax(test_code, "python", theme="monokai", line_numbers=True)

        panel = Panel(
            syntax,
            title=f"测试代码预览 - {test_filename}",
            border_style="green"
        )
        self.console.print(panel)

        # 显示代码统计
        lines = test_code.splitlines()
        non_empty_lines = [line for line in lines if line.strip()]

        # 统计测试用例数量
        test_case_count = sum(1 for line in lines if line.strip().startswith("def test_"))

        self.console.print(f"[dim]行数: {len(lines)} | 非空行: {len(non_empty_lines)} | 测试用例: {test_case_count}[/dim]")

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
                f"[bold yellow]⚠️  测试文件 {relative_path} 已存在，是否覆盖？[/bold yellow]",
                default=False
            )
            return confirm
        else:
            # 新文件，确认创建
            confirm = Confirm.ask(
                f"[bold yellow]创建新测试文件 {relative_path}？[/bold yellow]",
                default=True
            )
            return confirm

    def _create_backup(self, root_path: Path, original_file: Path) -> Path:
        """创建备份文件"""
        import time
        timestamp = int(time.time())
        backup_path = root_path / self.backup_dir / "tests"
        backup_path.mkdir(parents=True, exist_ok=True)
        backup_file = backup_path / f"{original_file.name}.backup.{timestamp}"

        # 复制文件
        shutil.copy2(original_file, backup_file)
        return backup_file

    def _show_test_file_stats(self, test_code: str, file_path: Path):
        """显示测试文件统计信息"""
        lines = test_code.splitlines()

        # 统计测试元素
        test_case_count = sum(1 for line in lines if line.strip().startswith("def test_"))
        test_class_count = sum(1 for line in lines if line.strip().startswith("class Test"))
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
        table = Table(title="测试文件统计", show_header=False, box=None)
        table.add_column("项目", style="cyan")
        table.add_column("数值", style="green")

        table.add_row("总行数", str(len(lines)))
        table.add_row("代码行", str(code_lines))
        table.add_row("注释行", str(comment_lines))
        table.add_row("空行", str(blank_lines))
        table.add_row("", "")  # 空行分隔
        table.add_row("测试用例", str(test_case_count))
        table.add_row("测试类", str(test_class_count))
        table.add_row("导入语句", str(import_count))

        self.console.print(table)

    def _show_test_run_suggestions(self, root_path: Path):
        """显示测试运行建议"""
        self.console.print("\n[bold]🚀 测试运行建议:[/bold]")

        suggestions = [
            "1. 运行所有测试: [cyan]pytest[/cyan]",
            "2. 运行特定测试文件: [cyan]pytest tests/test_generated.py[/cyan]",
            "3. 运行并显示详细信息: [cyan]pytest -v[/cyan]",
            "4. 运行并生成覆盖率报告: [cyan]pytest --cov=.[/cyan]",
            "5. 运行特定测试用例: [cyan]pytest -k 'test_function_name'[/cyan]",
        ]

        for suggestion in suggestions:
            self.console.print(f"   {suggestion}")

        # 检查pytest是否可用
        try:
            import subprocess
            result = subprocess.run(["pytest", "--version"],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.console.print(f"\n[dim]📦 {result.stdout.strip()}[/dim]")
        except:
            self.console.print("\n[dim]💡 提示: 确保已安装pytest (pip install pytest)[/dim]")


# 工具函数
def create_test_file_manager(console: Console) -> TestFileManager:
    """创建测试文件管理器"""
    return TestFileManager(console)
