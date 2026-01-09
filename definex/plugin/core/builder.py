import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import yaml
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from definex.plugin.core.utils import CommonUtils


class PluginBuilder:
    def __init__(self, console, validator):
        """
        console: Rich Console 实例
        validator: ProjectValidator 实例，用于前置校验
        """
        self.console = console
        self.validator = validator

    def run_build_flow(self, path: str):
        """执行完整的构建与打包工作流"""
        root = Path(path).resolve()

        # --- 1. 构建前置校验 (强制执行全量审计) ---
        if not self.validator.check_all(path):
            self.console.print("\n[bold red]❌ 构建终止: 插件合规性校验未通过，请根据提示修复。[/bold red]")
            return None

        # --- 2. 准备打包元数据 ---
        try:
            with open(root / "manifest.yaml", "r", encoding="utf-8") as f:
                m_data = yaml.safe_load(f)
                plugin_id = m_data.get("plugin_info", {}).get("id", root.name)
        except Exception as e:
            self.console.print(f"[red]❌ 读取 manifest 失败: {e}[/red]")
            return None

        pkg_name = f"{plugin_id}.dfxpkg"
        output_path = root.parent / pkg_name

        # --- 3. 开启进度显示 ---
        with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=40),
                TaskProgressColumn(),
                console=self.console,
                transient=True
        ) as progress:
            main_task = progress.add_task("🚀 准备启动构建流程...", total=100)

            # Step A: 依赖同步 (占 40%)
            progress.update(main_task, description="📦 正在同步并隔离运行环境 (libs/)...")
            if not self._sync_dependencies(root):
                return None
            progress.advance(main_task, 40)

            # Step B: 创建临时沙箱并组装 (占 20%)
            progress.update(main_task, description="🏗️  正在创建构建沙箱...")
            with tempfile.TemporaryDirectory(prefix="dfx_build_") as tmp_dir:
                tmp_path = Path(tmp_dir)

                # 复制核心组件 (明确排除 simple 目录)
                self._assemble_sandbox(root, tmp_path, progress, main_task)
                progress.advance(main_task, 20)

                # Step C: 环境清理 (占 10%)
                progress.update(main_task, description="🧹 正在清理冗余编译文件...")
                CommonUtils.cleanup_dir(tmp_path)
                progress.advance(main_task, 10)

                # Step D: 最终压缩封装 (占 30%)
                progress.update(main_task, description=f"🗜️  正在封装 {pkg_name}...")
                self._compress_pkg(tmp_path, output_path, progress, main_task)
                progress.update(main_task, completed=100, description="✨ 构建全量完成")

        self.console.print(f"\n[bold green]🎉 插件包构建成功![/bold green]")
        self.console.print(f"📂 产出文件: [cyan]{output_path}[/cyan]")
        self.console.print(f"💡 运行测试: [dim]dfx plugin run native {pkg_name} --action <NAME>[/dim]\n")
        return output_path

    def _sync_dependencies(self, root: Path) -> bool:
        """同步 requirements.txt 到本地 libs 目录 (带哈希缓存逻辑)"""
        req_file = root / "requirements.txt"
        libs_dir = root / "libs"
        hash_file = libs_dir / ".deps_hash"

        # 如果没有依赖文件，直接跳过
        if not req_file.exists() or req_file.stat().st_size == 0:
            self.console.print("[yellow]⚠️  未发现依赖声明，跳过依赖同步阶段。[/yellow]")
            return True

        current_hash = CommonUtils.get_file_hash(req_file)

        # 检查哈希缓存是否匹配
        if libs_dir.exists() and hash_file.exists():
            if hash_file.read_text().strip() == current_hash:
                self.console.print("[green]✨ 依赖哈希匹配，使用本地缓存 (libs/)。[/green]")
                return True

        # 执行 pip install -t
        if libs_dir.exists():
            shutil.rmtree(libs_dir)
        libs_dir.mkdir(parents=True)

        try:
            with self.console.status("[bold blue]正在执行隔离安装 (pip install -t libs)..."):
                result = subprocess.run([
                    sys.executable, "-m", "pip", "install",
                    "-r", str(req_file),
                    "--target", str(libs_dir),
                    "--no-cache-dir",
                    "--upgrade",
                    "--quiet"
                ], capture_output=True, text=True)

                if result.returncode != 0:
                    self.console.print(f"[red]❌ Pip 安装失败:[/red]\n{result.stderr}")
                    return False

            # 安装成功后写入哈希
            hash_file.write_text(current_hash)
            return True
        except Exception as e:
            self.console.print(f"[red]❌ 依赖构建异常: {e}[/red]")
            return False

    def _assemble_sandbox(self, root: Path, tmp_path: Path, progress, task_id):
        """将必要文件组装进临时沙箱，跳过 simple 目录"""
        # 定义核心必需文件/目录
        essential_items = ["tools", "libs", "manifest.yaml", "spec.md", "requirements.txt"]

        for item in essential_items:
            src = root / item
            if not src.exists():
                continue

            dest = tmp_path / item
            if src.is_dir():
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)

    def _compress_pkg(self, source_dir: Path, output_file: Path, progress, task_id):
        """执行压缩，并实时显示正在封装的文件"""
        all_files = list(source_dir.rglob("*"))
        # 过滤掉目录，只计文件
        only_files = [f for f in all_files if f.is_file()]

        if not only_files:
            return

        # 这里的 30 代表总进度的最后 30%
        step_unit = 30 / len(only_files)

        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in only_files:
                arcname = file_path.relative_to(source_dir)
                zipf.write(file_path, arcname)

                # 动态更新进度条下方的描述
                progress.advance(task_id, step_unit)
                progress.update(task_id, description=f"🗜️  封装: [dim]{arcname}[/dim]")