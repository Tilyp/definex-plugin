"""
项目分析器，负责分析项目结构
"""
from pathlib import Path
from typing import Dict

from rich.console import Console
from rich.panel import Panel


class ProjectAnalyzer:
    """项目结构分析器"""

    def __init__(self, console: Console):
        self.console = console
        self.cache = {}  # 缓存分析结果

    def analyze_project(self, root_path: Path, use_cache: bool = True) -> Dict[str, any]:
        """
        分析项目结构

        Args:
            root_path: 项目根目录
            use_cache: 是否使用缓存

        Returns:
            项目分析结果字典
        """
        root = Path(root_path).resolve()
        cache_key = str(root)

        # 使用缓存
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]

        analysis = {
            "root": root,
            "tools_dir": root / "tools",
            "has_tools_dir": False,
            "python_files": [],
            "main_file": None,
            "plugin_structure": {},
            "dependencies": [],
            "summary": ""
        }

        # 检查tools目录
        tools_dir = analysis["tools_dir"]
        if tools_dir.exists():
            analysis["has_tools_dir"] = True

            # 查找Python文件
            python_files = list(tools_dir.rglob("*.py"))
            analysis["python_files"] = python_files

            # 查找主文件
            main_file = tools_dir / "main.py"
            if main_file.exists():
                analysis["main_file"] = main_file

                # 分析主文件结构
                plugin_structure = self._analyze_plugin_file(main_file)
                analysis["plugin_structure"] = plugin_structure

        # 生成摘要
        analysis["summary"] = self._generate_summary(analysis)

        # 缓存结果
        self.cache[cache_key] = analysis

        return analysis

    def _analyze_plugin_file(self, file_path: Path) -> Dict[str, any]:
        """分析插件文件结构"""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")

            structure = {
                "imports": [],
                "classes": [],
                "actions": [],
                "inherits_base_plugin": False,
                "has_docstring": False,
                "line_count": len(content.splitlines())
            }

            lines = content.splitlines()

            # 分析导入
            for line in lines:
                line_stripped = line.strip()
                if line_stripped.startswith("import ") or line_stripped.startswith("from "):
                    structure["imports"].append(line_stripped)

            # 分析类和函数
            for i, line in enumerate(lines):
                line_stripped = line.strip()

                # 检查是否继承自BasePlugin
                if "BasePlugin" in line:
                    structure["inherits_base_plugin"] = True

                # 检查是否有docstring
                if '"""' in line or "'''" in line:
                    structure["has_docstring"] = True

                # 查找类定义
                if line_stripped.startswith("class "):
                    class_name = line_stripped.split("class ")[1].split("(")[0].strip()
                    structure["classes"].append(class_name)

                # 查找@action装饰器
                if "@action" in line:
                    # 查找对应的函数定义
                    for j in range(i + 1, min(i + 3, len(lines))):
                        if lines[j].strip().startswith("def "):
                            func_name = lines[j].strip().split("def ")[1].split("(")[0].strip()
                            structure["actions"].append(func_name)
                            break

            return structure

        except Exception as e:
            self.console.print(f"[yellow]警告: 分析文件 {file_path} 时出错: {e}[/yellow]")
            return {}

    def _generate_summary(self, analysis: Dict) -> str:
        """生成项目摘要"""
        summary_lines = []

        if not analysis["has_tools_dir"]:
            summary_lines.append("📁 tools目录不存在，将创建新的插件项目")
        elif not analysis["python_files"]:
            summary_lines.append("📁 tools目录为空，将创建新的插件")
        else:
            summary_lines.append(f"📁 tools目录包含 {len(analysis['python_files'])} 个Python文件")

            if analysis["main_file"]:
                structure = analysis["plugin_structure"]
                summary_lines.append(f"📄 主文件: main.py ({structure['line_count']} 行)")

                if structure["classes"]:
                    summary_lines.append(f"🧩 类定义: {', '.join(structure['classes'])}")

                if structure["actions"]:
                    summary_lines.append(f"🔧 Action函数: {', '.join(structure['actions'])}")

                if structure["inherits_base_plugin"]:
                    summary_lines.append("✅ 继承自 BasePlugin")
                else:
                    summary_lines.append("⚠️ 未继承 BasePlugin（需要修正）")

                if not structure["has_docstring"]:
                    summary_lines.append("📝 缺少文档字符串")

        return "\n".join(summary_lines)

    def display_analysis(self, analysis: Dict, title: str = "项目分析"):
        """显示项目分析结果"""
        panel_content = []

        panel_content.append(f"项目根目录: {analysis['root']}")
        panel_content.append("")

        # 添加摘要
        if analysis["summary"]:
            panel_content.append(analysis["summary"])

        # 如果有主文件，显示预览
        if analysis["main_file"]:
            panel_content.append("")
            panel_content.append("--- 主文件预览 ---")
            try:
                content = analysis["main_file"].read_text(encoding="utf-8", errors="ignore")
                # 只显示前30行
                preview_lines = content.splitlines()[:30]
                preview = "\n".join(preview_lines)
                if len(content.splitlines()) > 30:
                    preview += f"\n... 共 {len(content.splitlines())} 行"
                panel_content.append(preview)
            except Exception as e:
                panel_content.append(f"无法读取文件: {e}")

        # 创建并显示面板
        panel = Panel(
            "\n".join(panel_content),
            title=title,
            border_style="cyan"
        )
        self.console.print(panel)

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()