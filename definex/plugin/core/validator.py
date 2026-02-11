"""
DefineX 项目验证器
负责执行插件项目的合规性审计和验证
"""
from pathlib import Path
from typing import Dict, Any

import yaml
from rich.console import Console

from definex.plugin.core.annotation_validator import validate_actions
from definex.plugin.core.scanner import CodeScanner
from definex.plugin.sdk import DataTypes, MAX_NESTING_DEPTH


class ProjectValidator:
    """项目验证器，负责执行全量合规性审计"""
    def __init__(self, console: Console, scanner: CodeScanner) -> None:
        """
        初始化验证器

        Args:
            console: Rich Console 实例，用于彩色输出
            scanner: CodeScanner 实例，用于从源码实时提取事实
        """
        self.console = console
        self.scanner = scanner
        self.has_error = False

    def check_all(self, path: str) -> bool:
        """
        执行全量合规性审计

        Args:
            path: 插件项目根目录路径

        Returns:
            bool: 审计是否通过
        """
        root = Path(path).resolve()
        self.has_error = False
        self.console.print(f"\n[bold]🔍 开始审计插件项目:[/bold] [cyan]{root.name}[/cyan]")
        self.console.print("-" * 50)
        # 1. 静态安全审计
        self._check_security(root)
        # 2. 依赖规范审计 (requirements.txt)
        if not self._check_requirements(root):
            self.has_error = True
        # 3. 契约文件完整性审计
        manifest_path = root / "manifest.yaml"
        if not manifest_path.exists():
            self.console.print("[red]❌ 缺失 manifest.yaml，请先执行 dfx plugin manifest[/red]")
            return False
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = yaml.safe_load(f)
        except Exception as e:
            self.console.print(f"[red]❌ 解析 manifest.yaml 失败: {e}[/red]")
            return False
        # 4. 源码与契约一致性比对 (Alignment Check)
        if not self._check_code_alignment(manifest_data, root):
            self.has_error = True
        # 5. 契约内容深度合规性校验 (Recursive Schema Check)
        if not self._check_manifest_content(manifest_data):
            self.has_error = True
        # 6. 强制参数注解校验 (使用统一工具)
        if not self._check_parameter_annotations(root):
            self.has_error = True
        # 最终汇总
        if self.has_error:
            self.console.print("-" * 50)
            self.console.print("[bold red]🚨 审计未通过！请修正上述违规项后再行操作。[/bold red]\n")
            return False
        self.console.print("-" * 50)
        self.console.print("[bold green]✅ 契约一致，深度合规！项目已准备就绪。[/bold green]\n")
        return True

    def validate_project(self, path: str) -> bool:
        """
        验证项目 (用于 check 命令)

        Args:
            path: 插件项目根目录路径

        Returns:
            bool: 验证是否通过
        """
        return self.check_all(path)

    def _check_security(self, root: Path) -> None:
        """
        扫描危险的系统调用

        Args:
            root: 插件项目根目录
        """
        dangerous_calls = ["os.system", "subprocess.call", "eval(", "exec("]
        for py_file in (root / "tools").rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                for call in dangerous_calls:
                    if call in content:
                        self.console.print(f"[yellow]⚠️  警告: {py_file.relative_to(root)} 包含潜在危险调用: {call}[/yellow]")
            except Exception:
                pass

    def _check_requirements(self, root: Path) -> bool:
        """
        检查 requirements.txt 规范

        Args:
            root: 插件项目根目录

        Returns:
            bool: 是否合规
        """
        req_path = root / "requirements.txt"
        if not req_path.exists():
            self.console.print("[green]✅ 未发现 requirements.txt，跳过依赖检查[/green]")
            return True

        try:
            content = req_path.read_text(encoding="utf-8")
            lines = content.strip().split("\n")
            valid = True

            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # 检查基本格式
                if "==" not in line and ">=" not in line and "<=" not in line and "~=" not in line:
                    self.console.print(f"[red]❌ 第 {i} 行: '{line}' 缺少版本约束符 (建议使用 ==、>=、<= 或 ~=)[/red]")
                    valid = False
                elif line.count("=") > 2:
                    self.console.print(f"[yellow]⚠️  第 {i} 行: '{line}' 包含多个等号，可能格式错误[/yellow]")

            if valid:
                self.console.print("[green]✅ requirements.txt 格式合规[/green]")
            return valid

        except Exception as e:
            self.console.print(f"[red]❌ 读取 requirements.txt 失败: {e}[/red]")
            return False

    def _check_code_alignment(self, manifest_data: Dict[str, Any], root: Path) -> bool:
        """
        比对源码与契约的一致性

        Args:
            manifest_data: 契约数据
            root: 插件项目根目录

        Returns:
            bool: 是否一致
        """
        self.console.print("\n[bold blue]🔍 正在比对源码与契约一致性...[/bold blue]")

        # 从契约中提取 Action 名称
        manifest_actions = []
        if "actions" in manifest_data:
            manifest_actions = [a.get("name", "") for a in manifest_data["actions"]]

        # 从源码中实时提取 Action
        code_actions_list = self.scanner.scan_tools_directory(root)
        code_actions = [a.get("name", "") for a in code_actions_list]

        # 比对差异
        missing_in_code = set(manifest_actions) - set(code_actions)
        missing_in_manifest = set(code_actions) - set(manifest_actions)

        valid = True

        if missing_in_code:
            self.console.print("[red]❌ 契约中存在但源码中缺失的 Action:[/red]")
            for action in missing_in_code:
                self.console.print(f"    [red]✗ {action}[/red]")
            valid = False

        if missing_in_manifest:
            self.console.print("[red]❌ 源码中存在但契约中缺失的 Action:[/red]")
            for action in missing_in_manifest:
                self.console.print(f"    [red]✗ {action}[/red]")
            valid = False

        if valid:
            self.console.print(f"[green]✅ 源码与契约一致 ({len(manifest_actions)} 个 Action)[/green]")

        return valid

    def _check_manifest_content(self, manifest_data: Dict[str, Any]) -> bool:
        """
        深度校验契约内容

        Args:
            manifest_data: 契约数据

        Returns:
            bool: 是否合规
        """
        self.console.print("\n[bold blue]🔍 正在深度校验契约内容...[/bold blue]")

        if not manifest_data:
            self.console.print("[red]❌ 契约文件为空[/red]")
            return False

        # 检查 plugin_info
        if "plugin_info" not in manifest_data:
            self.console.print("[red]❌ 缺失 plugin_info 节[/red]")
            return False

        plugin_info = manifest_data["plugin_info"]
        required_fields = ["id", "name", "version", "description"]
        missing_fields = [field for field in required_fields if field not in plugin_info]

        if missing_fields:
            self.console.print(f"[red]❌ plugin_info 缺失必要字段: {', '.join(missing_fields)}[/red]")
            return False

        # 检查 actions
        if "actions" not in manifest_data:
            self.console.print("[red]❌ 缺失 actions 节[/red]")
            return False

        actions = manifest_data["actions"]
        if not actions:
            self.console.print("[red]❌ actions 列表为空[/red]")
            return False

        # 递归校验每个 Action 的 Schema
        valid = True
        for i, action in enumerate(actions):
            action_name = action.get("name", f"Action#{i}")

            # 校验 inputSchema
            if "inputSchema" in action:
                if not self._recursive_validate_schema(action["inputSchema"], f"{action_name}.inputSchema", 0):
                    valid = False

            # 校验 outputSchema
            if "outputSchema" in action:
                if not self._recursive_validate_schema(action["outputSchema"], f"{action_name}.outputSchema", 0):
                    valid = False

        if valid:
            self.console.print(f"[green]✅ 契约内容深度合规 ({len(actions)} 个 Action)[/green]")

        return valid

    def _check_parameter_annotations(self, root: Path) -> bool:
        """
        强制校验参数注解是否符合规范（使用统一工具）

        Args:
            root: 插件项目根目录

        Returns:
            bool: 参数注解是否合规
        """
        self.console.print("\n[bold blue]🔍 正在执行参数注解强制校验...[/bold blue]")

        # 使用扫描器获取所有 Action
        actions = self.scanner.scan_tools_directory(root)

        # 使用统一工具校验
        errors = validate_actions(actions)

        # 打印结果
        if not errors:
            self.console.print("[green]✅ 所有参数注解符合规范[/green]")
            return True
        else:
            self.console.print("[red]❌ 参数注解校验失败[/red]")
            for error in errors:
                self.console.print(f"    [red]✗ {error}[/red]")
            self.console.print("\n[bold yellow]💡 修正建议:[/bold yellow]")
            self.console.print("    1. 所有参数必须使用 Annotated[类型, \"描述\"] 格式")
            self.console.print("    2. Annotated 注解必须包含描述信息")
            self.console.print("    3. 示例: Annotated[str, \"用户名\"]")
            return False

    def _recursive_validate_schema(self, schema: Dict[str, Any], context: str, depth: int) -> bool:
        """
        核心：深度递归校验逻辑

        Args:
            schema: 要校验的 Schema 数据
            context: 当前校验的上下文路径（用于错误信息）
            depth: 当前递归深度

        Returns:
            bool: Schema 是否合规
        """
        # A. 深度限制拦截
        if depth > MAX_NESTING_DEPTH:
            self.console.print(f"[red]❌ {context}: Schema 嵌套深度超过限制 ({MAX_NESTING_DEPTH})[/red]")
            return False

        # B. 类型字段必填性检查
        if "type" not in schema:
            self.console.print(f"[red]❌ {context}: 缺失 'type' 字段[/red]")
            return False

        schema_type = schema["type"]

        # C. 类型枚举值合规性检查
        # if schema_type not in DataTypes.ALL_TYPES:
        #     self.console.print(f"[red]❌ {context}: 未知类型 '{schema_type}'，允许的类型: {', '.join(DataTypes.ALL_TYPES)}[/red]")
        #     return False

        # D. 递归处理对象类型
        if schema_type == "object":
            if "properties" not in schema:
                self.console.print(f"[red]❌ {context}: object 类型缺失 'properties' 字段[/red]")
                return False

            properties = schema["properties"]
            valid = True

            for prop_name, prop_schema in properties.items():
                prop_context = f"{context}.{prop_name}"
                if not self._recursive_validate_schema(prop_schema, prop_context, depth + 1):
                    valid = False

            return valid

        # E. 递归处理数组类型
        elif schema_type == "array":
            if "items" not in schema:
                self.console.print(f"[red]❌ {context}: array 类型缺失 'items' 字段[/red]")
                return False

            items_context = f"{context}.items"
            return self._recursive_validate_schema(schema["items"], items_context, depth + 1)

        # F. 基础类型直接通过
        else:
            return True
