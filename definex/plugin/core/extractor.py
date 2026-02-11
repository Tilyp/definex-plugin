"""
DefineX 插件包解压工具
负责解压 .dfxpkg 文件到指定目录
"""

import zipfile
import sys
from pathlib import Path
from typing import Optional

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console


class PluginExtractor:
    """插件包解压器"""

    def __init__(self, console: Optional[Console] = None):
        """
        初始化解压器

        Args:
            console: Rich Console 实例，如果为 None 则创建新的
        """
        self.console = console or Console()

    def extract_package(self, pkg_path: str, output_dir: Optional[str] = None) -> Path:
        """
        解压 .dfxpkg 文件到指定目录

        Args:
            pkg_path: .dfxpkg 文件路径
            output_dir: 输出目录，如果为 None 则解压到当前目录的插件名目录

        Returns:
            Path: 解压后的目录路径

        Raises:
            FileNotFoundError: 如果 pkg_path 不存在
            ValueError: 如果文件不是 .dfxpkg 格式
            zipfile.BadZipFile: 如果 ZIP 文件损坏
        """
        pkg_file = Path(pkg_path).resolve()

        # 验证文件存在且是 .dfxpkg 格式
        if not pkg_file.exists():
            raise FileNotFoundError(f"文件不存在: {pkg_path}")

        if pkg_file.suffix != ".dfxpkg":
            raise ValueError(f"文件必须是 .dfxpkg 格式，当前文件: {pkg_file.suffix}")

        # 确定输出目录
        if output_dir:
            output_path = Path(output_dir).resolve()
        else:
            # 默认使用插件名作为目录名（去掉 .dfxpkg 后缀）
            plugin_name = pkg_file.stem
            output_path = pkg_file.parent / plugin_name

        # 确保输出目录存在
        output_path.mkdir(parents=True, exist_ok=True)

        self.console.print(f"[bold]📦 开始解压插件包:[/bold] [cyan]{pkg_file.name}[/cyan]")
        self.console.print(f"[bold]📂 输出目录:[/bold] [cyan]{output_path}[/cyan]")
        self.console.print("-" * 50)

        # 执行解压
        success = self._extract_with_progress(pkg_file, output_path)

        if success:
            self.console.print(f"\n[bold green]✅ 解压成功![/bold green]")
            self.console.print(f"[bold]📁 解压到:[/bold] [cyan]{output_path}[/cyan]")

            # 显示解压内容概览
            self._show_extracted_contents(output_path)
        else:
            self.console.print(f"\n[bold red]❌ 解压失败[/bold red]")

        return output_path

    def _extract_with_progress(self, pkg_file: Path, output_dir: Path) -> bool:
        """
        使用进度条显示解压过程

        Args:
            pkg_file: .dfxpkg 文件路径
            output_dir: 输出目录

        Returns:
            bool: 解压是否成功
        """
        try:
            with zipfile.ZipFile(pkg_file, 'r') as zipf:
                # 获取所有文件列表
                file_list = zipf.namelist()
                total_files = len(file_list)

                if total_files == 0:
                    self.console.print("[yellow]⚠️  压缩包为空[/yellow]")
                    return True

                # 创建进度条
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[bold blue]{task.description}"),
                    BarColumn(bar_width=40),
                    TaskProgressColumn(),
                    console=self.console,
                    transient=True
                ) as progress:
                    task = progress.add_task(
                        f"📦 正在解压 {total_files} 个文件...",
                        total=total_files
                    )

                    # 逐个解压文件
                    for i, filename in enumerate(file_list, 1):
                        try:
                            # 更新进度描述
                            progress.update(
                                task,
                                description=f"📦 解压: [dim]{filename}[/dim]"
                            )

                            # 解压文件
                            zipf.extract(filename, output_dir)

                            # 更新进度
                            progress.advance(task)

                        except Exception as e:
                            self.console.print(
                                f"[red]❌ 解压文件失败 {filename}: {e}[/red]"
                            )
                            return False

                return True

        except zipfile.BadZipFile as e:
            self.console.print(f"[red]❌ ZIP 文件损坏: {e}[/red]")
            return False
        except Exception as e:
            self.console.print(f"[red]❌ 解压过程出错: {e}[/red]")
            return False

    def _show_extracted_contents(self, output_dir: Path):
        """
        显示解压后的内容概览

        Args:
            output_dir: 解压后的目录
        """
        try:
            # 统计文件和目录
            all_items = list(output_dir.rglob("*"))
            files = [f for f in all_items if f.is_file()]
            dirs = [d for d in all_items if d.is_dir()]

            self.console.print(f"\n[bold]📊 解压内容统计:[/bold]")
            self.console.print(f"  📁 目录数量: {len(dirs)}")
            self.console.print(f"  📄 文件数量: {len(files)}")

            # 显示关键文件
            key_files = [
                "manifest.yaml",
                "requirements.txt",
                "__init__.py",
                "main.py"
            ]

            found_key_files = []
            for key_file in key_files:
                if (output_dir / key_file).exists():
                    found_key_files.append(key_file)

            if found_key_files:
                self.console.print(f"\n[bold]🔑 关键文件:[/bold]")
                for key_file in found_key_files:
                    self.console.print(f"  ✅ {key_file}")

            # 显示总大小
            total_size = sum(f.stat().st_size for f in files)
            size_mb = total_size / (1024 * 1024)
            self.console.print(f"\n[bold]💾 总大小:[/bold] {size_mb:.2f} MB")

        except Exception as e:
            self.console.print(f"[yellow]⚠️  无法统计解压内容: {e}[/yellow]")

    def list_package_contents(self, pkg_path: str):
        """
        列出 .dfxpkg 文件内容而不解压

        Args:
            pkg_path: .dfxpkg 文件路径
        """
        pkg_file = Path(pkg_path).resolve()

        if not pkg_file.exists():
            self.console.print(f"[red]❌ 文件不存在: {pkg_path}[/red]")
            return

        if pkg_file.suffix != ".dfxpkg":
            self.console.print(f"[red]❌ 文件必须是 .dfxpkg 格式[/red]")
            return

        try:
            with zipfile.ZipFile(pkg_file, 'r') as zipf:
                file_list = zipf.namelist()
                total_files = len(file_list)

                self.console.print(f"[bold]📦 插件包内容: {pkg_file.name}[/bold]")
                self.console.print(f"[bold]📄 文件总数:[/bold] {total_files}")
                self.console.print("-" * 50)

                # 按目录分组显示
                dir_structure = {}
                for filename in sorted(file_list):
                    parts = filename.split('/')
                    if len(parts) > 1:
                        dir_name = parts[0]
                        if dir_name not in dir_structure:
                            dir_structure[dir_name] = []
                        dir_structure[dir_name].append('/'.join(parts[1:]) or "(目录)")
                    else:
                        if "." not in dir_structure:
                            dir_structure["."] = []
                        dir_structure["."].append(filename)

                # 显示目录结构
                for dir_name, files in dir_structure.items():
                    if dir_name == ".":
                        self.console.print(f"[bold]📁 根目录:[/bold]")
                    else:
                        self.console.print(f"[bold]📁 {dir_name}/:[/bold]")

                    for file in sorted(files):
                        if file == "(目录)":
                            self.console.print(f"  📁 {dir_name}/")
                        else:
                            self.console.print(f"  📄 {file}")

                    self.console.print()

        except zipfile.BadZipFile as e:
            self.console.print(f"[red]❌ ZIP 文件损坏: {e}[/red]")
        except Exception as e:
            self.console.print(f"[red]❌ 读取文件失败: {e}[/red]")

    def verify_package(self, pkg_path: str) -> bool:
        """
        验证 .dfxpkg 文件完整性

        Args:
            pkg_path: .dfxpkg 文件路径

        Returns:
            bool: 文件是否完整有效
        """
        pkg_file = Path(pkg_path).resolve()

        if not pkg_file.exists():
            self.console.print(f"[red]❌ 文件不存在: {pkg_path}[/red]")
            return False

        if pkg_file.suffix != ".dfxpkg":
            self.console.print(f"[red]❌ 文件必须是 .dfxpkg 格式[/red]")
            return False

        self.console.print(f"[bold]🔍 验证插件包: {pkg_file.name}[/bold]")

        try:
            with zipfile.ZipFile(pkg_file, 'r') as zipf:
                # 测试 ZIP 文件完整性
                test_result = zipf.testzip()

                if test_result is not None:
                    self.console.print(f"[red]❌ 文件损坏: {test_result}[/red]")
                    return False

                # 检查必要文件
                required_files = ["manifest.yaml"]
                missing_files = []

                for required_file in required_files:
                    if required_file not in zipf.namelist():
                        missing_files.append(required_file)

                if missing_files:
                    self.console.print(f"[red]❌ 缺少必要文件: {', '.join(missing_files)}[/red]")
                    return False

                self.console.print("[green]✅ 插件包验证通过[/green]")
                return True

        except zipfile.BadZipFile as e:
            self.console.print(f"[red]❌ ZIP 文件损坏: {e}[/red]")
            return False
        except Exception as e:
            self.console.print(f"[red]❌ 验证过程出错: {e}[/red]")
            return False


def main():
    """命令行入口函数"""
    import argparse

    parser = argparse.ArgumentParser(description="DefineX 插件包解压工具")
    parser.add_argument("command", choices=["extract", "list", "verify"],
                       help="命令: extract(解压), list(列出内容), verify(验证)")
    parser.add_argument("pkg_file", help=".dfxpkg 文件路径")
    parser.add_argument("-o", "--output", help="输出目录（仅 extract 命令需要）")
    parser.add_argument("--no-progress", action="store_true",
                       help="不显示进度条")

    args = parser.parse_args()

    console = Console()
    extractor = PluginExtractor(console)

    try:
        if args.command == "extract":
            extractor.extract_package(args.pkg_file, args.output)
        elif args.command == "list":
            extractor.list_package_contents(args.pkg_file)
        elif args.command == "verify":
            extractor.verify_package(args.pkg_file)
    except Exception as e:
        console.print(f"[red]❌ 执行失败: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
