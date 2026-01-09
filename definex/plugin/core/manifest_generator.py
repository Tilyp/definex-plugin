"""
DefineX 契约文件生成器
负责从源码中提取 Action 信息并生成 manifest.yaml
"""
from pathlib import Path
from typing import Dict, Any, List

import yaml
from rich.console import Console

from definex.plugin.core.annotation_validator import validate_actions, print_errors_with_guidance
from definex.plugin.core.scanner import CodeScanner


class ManifestGenerator:
     """契约文件生成器"""

     def __init__(self, console: Console, scanner: CodeScanner):
         self.console = console
         self.scanner = scanner

     def generate(self, path: str, intent: str = "default") -> None:
         """
         生成契约文件

         Args:
             path: 插件项目根目录路径
             intent: 扫描意图模式
         """
         root = Path(path).resolve()

         self.console.print(f"[bold cyan]📄 正在生成契约文件 (模式: {intent})...[/bold cyan]")

         # 使用智能扫描器
         actions = self.scanner.scan_tools_directory_smart(root, intent)

         if not actions:
             self.console.print("[red]❌ 未发现任何 Action，请检查 tools/ 目录结构[/red]")
             return

         # 检查参数注解是否符合规范（使用统一工具）
         errors = validate_actions(actions)
         if not print_errors_with_guidance(errors, "生成契约文件"):
             return

         # 构建 manifest 数据结构
         manifest_data = self._build_manifest_data(actions, root)

         # 写入文件
         manifest_path = root / "manifest.yaml"
         with open(manifest_path, "w", encoding="utf-8") as f:
             yaml.dump(manifest_data, f, allow_unicode=True, sort_keys=False)

         self.console.print(f"[bold green]✅ 契约文件已生成: {manifest_path}[/bold green]")
         self.console.print(f"[dim]📊 统计: {len(actions)} 个 Action 已收录[/dim]")

     def _build_manifest_data(self, actions: List[Dict[str, Any]], root: Path) -> Dict[str, Any]:
         """
         构建 manifest 数据结构

         Args:
             actions: Action 列表
             root: 项目根目录

         Returns:
             Dict[str, Any]: manifest 数据
         """
         # 清理 Action 数据，移除内部字段
         cleaned_actions = []
         for action in actions:
             cleaned_action = {
                 "name": action["name"],
                 "category": action.get("category", "exec"),
                 "description": action.get("description", ""),
                 "location": action.get("location", {}),
                 "inputSchema": action.get("inputSchema", {}),
                 "outputSchema": action.get("outputSchema", {})
             }
             cleaned_actions.append(cleaned_action)

         # 尝试读取现有的 plugin_info
         existing_manifest = root / "manifest.yaml"
         plugin_info = {
             "id": root.name,
             "name": root.name,
             "version": "0.1.0",
             "description": f"{root.name} plugin"
         }

         if existing_manifest.exists():
             try:
                 with open(existing_manifest, "r", encoding="utf-8") as f:
                     existing_data = yaml.safe_load(f)
                     if existing_data and "plugin_info" in existing_data:
                         # 保留现有的 plugin_info，只更新必要的字段
                         existing_info = existing_data["plugin_info"]
                         plugin_info.update({
                             "id": existing_info.get("id", root.name),
                             "name": existing_info.get("name", root.name),
                             "version": existing_info.get("version", "0.1.0"),
                             "description": existing_info.get("description", f"{root.name} plugin")
                         })
             except Exception:
                 pass

         return {
             "plugin_info": plugin_info,
             "actions": cleaned_actions
         }
