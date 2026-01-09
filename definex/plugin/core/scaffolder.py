import random
import shutil
import string
import subprocess
import sys
import venv
from pathlib import Path

import yaml
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.table import Table

from definex.plugin.sdk import ICON_LIBRARY


class ProjectScaffolder:
    def __init__(self, console):
        # 准确定位模板根目录
        self.console = console
        self.template_root = Path(__file__).parent.parent / "templates"

    def _generate_id(self):
        """生成 16 位全局唯一标识符"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    def _select_icon(self):
        """格式化图标展示表"""
        table = Table(title="DefineX 图标库", show_header=True, header_style="bold magenta", box=None)
        table.add_column("编号", justify="right", style="dim")
        table.add_column("图标")
        table.add_column("分类", width=20)
        table.add_column("编号", justify="right", style="dim")
        table.add_column("图标")
        table.add_column("分类", width=20)

        keys = list(ICON_LIBRARY.keys())
        for i in range(0, len(keys), 2):
            k1 = keys[i]
            r = [k1, ICON_LIBRARY[k1]["icon"], ICON_LIBRARY[k1]["label"]]
            if i + 1 < len(keys):
                k2 = keys[i+1]
                r.extend([k2, ICON_LIBRARY[k2]["icon"], ICON_LIBRARY[k2]["label"]])
            else:
                r.extend(["", "", ""])
            table.add_row(*r)

        self.console.print(table)
        choice = self.console.input(f"[bold]请选择图标编号 (1-{len(ICON_LIBRARY)}, 默认 1): [/bold]") or "1"
        return ICON_LIBRARY.get(choice, ICON_LIBRARY["1"])["icon"]

    def run_init_flow(self, name):
        """主初始化工作流"""
        plugin_root = Path(name).resolve()
        if plugin_root.exists():
            self.console.print(f"[red]❌ 错误: 目录 '{name}' 已存在，请更换名称。[/red]")
            return

        # --- 1. 交互收集元数据 ---
        self.console.print(Panel(f"[bold blue]DefineX 插件项目初始化[/bold blue]\n项目名称: {name}", expand=False))
        author = self.console.input("👤 [bold]作者名称[/bold] (默认 DefineX): ") or "DefineX"
        version = self.console.input("🏷️[bold]初始版本[/bold] (默认 1.0.0): ") or "1.0.0"
        desc = self.console.input("📝 [bold]插件描述[/bold]: ") or f"DefineX 业务插件: {name}"
        icon = self._select_icon()

        self.console.print("\n[bold]开发环境偏好:[/bold]")
        self.console.print("  [1] 系统环境 (System Python)")
        self.console.print("  [2] 虚拟环境 (Isolated Venv) - [green]推荐，含 SDK 代码补全[/green]")
        env_choice = self.console.input("\n请选择编号 (1-2, 默认 2): ") or "2"

        # --- 2. 细粒度进度控制 ---
        plugin_id = self._generate_id()

        with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=40),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=self.console
        ) as progress:
            # 定义 10 个子任务步骤
            total_steps = 10
            task = progress.add_task("正在构建项目...", total=total_steps)

            # Step 1: 物理目录
            progress.update(task, description="📁 创建项目根目录...")
            plugin_root.mkdir(parents=True)
            progress.advance(task)

            # Step 2: 核心结构
            progress.update(task, description="📂 初始化 tools/ 和 simple/ 目录...")
            (plugin_root / "tools").mkdir()
            (plugin_root / "simple").mkdir()
            progress.advance(task)

            # Step 3: Manifest
            progress.update(task, description="📑 生成插件元数据契约 (manifest.yaml)...")
            self._write_manifest(plugin_root, name, plugin_id, author, version, desc, icon)
            progress.advance(task)

            # Step 4: Logic Entry
            progress.update(task, description="🐍 注入主逻辑模板 (tools/main.py)...")
            self._inject_template(plugin_root / "tools" / "main.py", "main.py.tmpl", {"class_name": self._to_camel_case(name)})
            progress.advance(task)

            # Step 5: Requirements
            progress.update(task, description="📋 生成依赖清单 (requirements.txt)...")
            self._inject_template(plugin_root / "requirements.txt", "requirements.txt.tmpl", {})
            progress.advance(task)

            # Step 6: Spec & Ignore
            progress.update(task, description="📖 生成开发手册 (spec.md)...")
            self._inject_template(plugin_root / "spec.md", "spec.md.tmpl", {
                "plugin_id": plugin_id,
                "plugin_name": name,
                "env_type": "虚拟环境" if env_choice == "2" else "系统环境"
            })
            self._inject_template(plugin_root / ".gitignore", ".gitignore.tmpl", {"plugin_name": name})
            progress.advance(task)

            # Step 7: Simple Examples
            progress.update(task, description="📝 注入分类开发样例 (simple/*.py)...")
            self._copy_simple_samples(plugin_root)
            progress.advance(task)

            # Step 8-10: 环境构建 (如果是虚拟环境模式)
            if env_choice == "2":
                venv_dir = plugin_root / f"{name}_venv"
                progress.update(task, description=f"🛠️  创建虚拟环境: {venv_dir.name}...")
                venv.create(venv_dir, with_pip=True)
                progress.advance(task)

                progress.update(task, description="⚡ 升级环境中的 Pip 工具...")
                python_exe = venv_dir / ("Scripts\\python.exe" if sys.platform == "win32" else "bin/python")
                subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], capture_output=True)
                progress.advance(task)

                progress.update(task, description="📦 正在安装核心依赖 (mcp/rich/fastmcp)...")
                subprocess.run([str(python_exe), "-m", "pip", "install", "-r", str(plugin_root / "requirements.txt")], capture_output=True)
                progress.advance(task)
            else:
                progress.advance(task, advance=3) # 跳过环境步骤

            progress.update(task, description="✨ 项目初始化全量完成！")

        # --- 3. 完工总结报告 ---
        self._print_success_summary(name, plugin_root, plugin_id, env_choice)

    # --- 内部辅助方法 ---
    def _to_camel_case(self, text):
        return "".join(x.capitalize() for x in text.replace("-", "_").split("_"))

    def _write_manifest(self, plugin_root, name, pid, author, ver, desc, icon):
        data = {
            "plugin_info": {
                "id": pid, "name": name, "author": author,
                "version": ver, "description": desc, "icon": icon
            },
            "actions": []
        }
        with open(plugin_root / "manifest.yaml", "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def _inject_template(self, target_path, tmpl_name, variables):
        tmpl_path = self.template_root / tmpl_name
        if not tmpl_path.exists():
            content = f"# Template {tmpl_name} not found"
        else:
            content = tmpl_path.read_text(encoding="utf-8")
            for k, v in variables.items():
                content = content.replace(f"{{{{ {k} }}}}", v)
        target_path.write_text(content, encoding="utf-8")

    def _copy_simple_samples(self, root):
        s_dir = self.template_root / "simple"
        if s_dir.exists():
            for f in s_dir.glob("*.tmpl"):
                target_f = root / "simple" / f.name.replace(".tmpl", "")
                shutil.copy(f, target_f)

    def _print_success_summary(self, name, plugin_root, pid, env_choice):
        venv_name = f"{name}_venv"
        act_cmd = f"source {venv_name}/bin/activate" if sys.platform != "win32" else f"{venv_name}\\Scripts\\activate"

        summary = (
            f"[bold green]🎉 恭喜！{name} 插件已就绪[/bold green]\n\n"
            f"🆔 [bold]项目 ID:[/bold]  {pid}\n"
            f"📂 [bold]项目路径:[/bold] {plugin_root}\n"
        )
        if env_choice == "2":
            summary += f"🛠️ [bold]激活环境:[/bold] [cyan]cd {name} && {act_cmd}[/cyan]\n"

        summary += f"🚀 [bold]下一步:[/bold]   [yellow]dfx plugin manifest[/yellow]"

        self.console.print(Panel(summary, title="DefineX Scaffolder", border_style="green", expand=False))