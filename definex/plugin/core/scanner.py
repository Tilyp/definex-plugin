"""
DefineX 代码扫描器
使用 AST 进行快速扫描，配合缓存机制提升性能
支持增量扫描和优化后的AST遍历
"""
import ast
import hashlib
import importlib.util
import inspect
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Any, get_type_hints

from definex.plugin.core.optimizer import create_scanner_with_intent
from definex.plugin.core.translator import SchemaTranslator
from definex.plugin.sdk import BasePlugin, DataTypes


class CacheManager:
    """扫描缓存管理器"""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        初始化缓存管理器

        Args:
            cache_dir: 缓存目录，默认为 ~/.definex/.cache
        """
        self.cache_dir = cache_dir or Path.home() / ".definex" / ".cache" / "scanner"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _make_cache_key(self, plugin_root: Path) -> str:
        """生成缓存键"""
        root_str = str(plugin_root.resolve())
        return hashlib.md5(root_str.encode()).hexdigest()

    def _get_cache_file(self, plugin_root: Path) -> Path:
        """获取缓存文件路径"""
        cache_key = self._make_cache_key(plugin_root)
        return self.cache_dir / f"{cache_key}.json"

    def is_cache_valid(self, plugin_root: Path, py_files: List[Path]) -> bool:
        """检查缓存是否有效"""
        cache_file = self._get_cache_file(plugin_root)

        if not cache_file.exists():
            return False

        # 检查文件修改时间
        cache_mtime = cache_file.stat().st_mtime
        for py_file in py_files:
            try:
                if py_file.stat().st_mtime > cache_mtime:
                    return False
            except (IOError, OSError):
                return False

        return True

    def load_cache(self, plugin_root: Path) -> Optional[List[Dict]]:
        """加载缓存"""
        cache_file = self._get_cache_file(plugin_root)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            return None

    def save_cache(self, plugin_root: Path, data: List[Dict]) -> None:
        """保存缓存"""
        cache_file = self._get_cache_file(plugin_root)

        with self._lock:
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except (IOError, OSError):
                pass  # 缓存保存失败，不影响主流程

    def clear_cache(self, plugin_root: Optional[Path] = None) -> None:
        """清除缓存"""
        if plugin_root:
            cache_file = self._get_cache_file(plugin_root)
            if cache_file.exists():
                cache_file.unlink()
        else:
            # 清除所有缓存
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)


class OptimizedASTScanner(ast.NodeVisitor):
     """优化的AST扫描器，使用NodeVisitor模式"""

     def __init__(self):
         self.actions = []
         self.current_class = None

     def visit_ClassDef(self, node: ast.ClassDef) -> None:
         """访问类定义节点"""
         # 检查是否继承BasePlugin
         if self._inherits_base_plugin(node):
             self.current_class = node.name
             # 继续访问类体
             self.generic_visit(node)
             self.current_class = None
         else:
             # 不继承BasePlugin的类，跳过其内部方法
             pass

     def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
         """访问函数定义节点"""
         if self.current_class is not None and self._has_action_decorator(node):
             action = self._extract_action_from_ast(node, self.current_class)
             self.actions.append(action)

     def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
         """访问异步函数定义节点"""
         if self.current_class is not None and self._has_action_decorator(node):
             action = self._extract_action_from_ast(node, self.current_class)
             self.actions.append(action)

     def _inherits_base_plugin(self, class_node: ast.ClassDef) -> bool:
         """检查类是否继承BasePlugin"""
         for base in class_node.bases:
             if isinstance(base, ast.Name) and base.id == "BasePlugin":
                 return True
             # 处理更复杂的继承情况，如 ast.Attribute
             elif isinstance(base, ast.Attribute):
                 if base.attr == "BasePlugin":
                     return True
         return False

     def _has_action_decorator(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
         """检查函数是否有@action装饰器，支持普通函数和异步函数"""
         for decorator in func_node.decorator_list:
             if isinstance(decorator, ast.Call):
                 if isinstance(decorator.func, ast.Name) and decorator.func.id == "action":
                     return True
             elif isinstance(decorator, ast.Name) and decorator.id == "action":
                 return True
         return False

     def _extract_action_from_ast(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef, class_name: str) -> Dict[str, Any]:
         """从AST节点提取Action元数据，支持普通函数和异步函数"""
         return {
             "name": func_node.name,
             "class_name": class_name,
             "docstring": ast.get_docstring(func_node) or "",
             "lineno": func_node.lineno,
             "args": [arg.arg for arg in func_node.args.args if arg.arg != 'self'],
             "returns": self._extract_return_annotation(func_node),
             "is_async": isinstance(func_node, ast.AsyncFunctionDef)
         }

     def _extract_return_annotation(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> Optional[str]:
         """提取返回类型注解，支持普通函数和异步函数"""
         if func_node.returns:
             return ast.unparse(func_node.returns) if hasattr(ast, 'unparse') else str(func_node.returns)
         return None

     @classmethod
     def extract_action_signatures(cls, file_path: Path) -> List[Dict[str, Any]]:
         """
         使用优化的AST扫描提取Action签名

         Args:
             file_path: Python文件路径

         Returns:
             Action签名列表
         """
         try:
             with open(file_path, 'r', encoding='utf-8') as f:
                 content = f.read()
                 tree = ast.parse(content)
         except (SyntaxError, IOError, UnicodeDecodeError):
             return []

         scanner = cls()
         scanner.visit(tree)
         return scanner.actions


class CodeScanner:
    """优化的代码扫描器"""

    def __init__(self, console, use_cache: bool = True, cache_dir: Optional[Path] = None):
        """
        初始化扫描器

        Args:
            console: Rich Console 实例
            use_cache: 是否启用缓存
            cache_dir: 缓存目录
        """
        self.console = console
        self.use_cache = use_cache
        self.cache_mgr = CacheManager(cache_dir) if use_cache else None
        self._ast_cache = {}  # 内存缓存
        self._lock = threading.Lock()

    def scan_tools_directory(self, plugin_root: Path) -> List[Dict[str, Any]]:
        """
        扫描 tools 目录并提取所有 Action

        优化策略：
        1. 检查文件级缓存
        2. 使用 AST 快速扫描签名
        3. 仅对修改的文件进行完整解析
        4. 缓存结果
        """
        # 确保 plugin_root 是绝对路径
        plugin_root = plugin_root.resolve()

        tools_dir = plugin_root / "tools"

        if not tools_dir.exists():
            return []

        py_files = list(tools_dir.rglob("*.py"))
        py_files = [f for f in py_files if not f.name.startswith("__")]

        # 1. 检查全量缓存
        if self.use_cache and self.cache_mgr.is_cache_valid(plugin_root, py_files):
            cached_actions = self.cache_mgr.load_cache(plugin_root)
            if cached_actions:
                self.console.print("[green]✨ 使用缓存的扫描结果[/green]")
                return cached_actions

        # 2. 快速 AST 扫描获取签名
        self.console.print("[bold cyan]🔍 正在扫描 tools 目录...[/bold cyan]")

        all_actions = []

        # 使用多线程加速 AST 扫描
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(OptimizedASTScanner.extract_action_signatures, f): f
                for f in py_files
            }

            for future in futures:
                py_file = futures[future]
                try:
                    actions_sig = future.result()
                    for action_sig in actions_sig:
                        # 添加文件路径信息
                        action_sig["file_path"] = str(py_file)
                        all_actions.append(action_sig)
                        self.console.print(
                            f"  [green]✓[/green] {py_file.name}: "
                            f"{action_sig['class_name']}.{action_sig['name']}"
                        )
                except Exception as e:
                    self.console.print(f"  [red]✗ {py_file.name}: {e}[/red]")

        # 3. 对所有签名进行完整解析（需要类型信息）
        self.console.print("[bold cyan]⚙️ 正在解析类型信息...[/bold cyan]")
        full_actions = self._enrich_with_types(all_actions, plugin_root, py_files)

        # 4. 保存缓存
        if self.use_cache:
            self.cache_mgr.save_cache(plugin_root, full_actions)

        return full_actions

    def _enrich_with_types(self, action_sigs: List[Dict[str, Any]], plugin_root: Path, py_files: List[Path]) -> List[Dict[str, Any]]:
        """
        为 Action 签名补充类型信息

        此步骤需要加载模块以获取完整的类型注解
        """
        full_actions = []
        tools_path = str(plugin_root / "tools")

        if tools_path not in sys.path:
            sys.path.insert(0, tools_path)

        try:
            for action_sig in action_sigs:
                abs_file_path = Path(action_sig["file_path"]).resolve()

                try:
                    # 动态加载模块
                    module = self._load_module(abs_file_path)

                    # 获取类和方法
                    cls = getattr(module, action_sig["class_name"], None)
                    if cls is None:
                        continue

                    method = getattr(cls, action_sig["name"], None)
                    if method is None:
                        continue

                    # 完整解析
                    full_action = self._parse_to_meta(
                        action_sig["name"],
                        method,
                        action_sig["class_name"],
                        abs_file_path,
                        plugin_root
                    )
                    full_actions.append(full_action)

                except Exception as e:
                    self.console.print(f"  [yellow]⚠️ 解析失败 {action_sig['name']}: {e}[/yellow]")

        finally:
            if tools_path in sys.path:
                sys.path.remove(tools_path)

        return full_actions

    def _load_module(self, file_path: Path) -> Any:
        """加载 Python 模块"""
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, str(file_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _parse_to_meta(self, m_name: str, method: Any, class_name: str, abs_file_path: Path, plugin_root: Path) -> Dict[str, Any]:
        """解析方法为 Action 元数据"""
        # 确保 plugin_root 是 Path 对象
        if not isinstance(plugin_root, Path):
            plugin_root = Path(plugin_root).resolve()

        # 确保 abs_file_path 是 Path 对象
        if not isinstance(abs_file_path, Path):
            abs_file_path = Path(abs_file_path).resolve()

        try:
            hints = get_type_hints(method, include_extras=True)
        except Exception:
            hints = {}

        sig = inspect.signature(method)

        # 1. 解析 inputSchema
        properties = {}
        required = []
        validation_warnings = []  # 新增：存储校验警告

        for p_name, param in sig.parameters.items():
            if p_name == 'self':
                continue

            # 获取参数类型
            param_type = hints.get(p_name)

            # 获取参数默认值
            default_val = param.default if param.default is not inspect.Parameter.empty else inspect.Parameter.empty

            # 解析参数类型，传入默认值
            param_schema = SchemaTranslator.resolve_type(param_type, default_val=default_val)

            # 检查是否required
            # 规则：
            # 1. 如果参数有默认值，则不是必填
            # 2. 如果参数没有默认值，但是类型中有 Required 标记，则是必填
            # 3. 如果参数没有默认值，也没有 Required 标记，则是必填
            if param.default is inspect.Parameter.empty:
                # 参数没有默认值
                is_required = True
            else:
                # 参数有默认值
                is_required = False

            properties[p_name] = param_schema
            if is_required:
                required.append(p_name)

            # 新增：检查参数注解是否符合规范
            if param_type is not None:
                from typing import get_origin
                origin = get_origin(param_type)

                # 检查是否是 Annotated 类型
                is_annotated = False
                if origin is not None:
                    # 检查是否是 typing._AnnotatedAlias 或 Annotated
                    try:
                        from typing import _AnnotatedAlias
                        if isinstance(param_type, _AnnotatedAlias):
                            is_annotated = True
                    except ImportError:
                        # 回退方法：检查字符串表示
                        if 'Annotated' in str(origin):
                            is_annotated = True

                if not is_annotated:
                    # 不是 Annotated 类型，记录警告
                    validation_warnings.append({
                        "type": "parameter_annotation",
                        "param": p_name,
                        "message": f"参数 '{p_name}' 应该使用 Annotated[str, \"描述\"] 格式"
                    })
                else:
                    # 检查是否有描述
                    try:
                        from typing import get_args
                        args = get_args(param_type)
                        if len(args) < 2 or not isinstance(args[1], str):
                            validation_warnings.append({
                                "type": "parameter_description",
                                "param": p_name,
                                "message": f"参数 '{p_name}' 的 Annotated 注解缺少描述"
                            })
                    except Exception:
                        pass

        # 2. 解析 outputSchema
        output_res = SchemaTranslator.resolve_type(hints.get('return'))

        # 3. 计算相对路径
        try:
            relative_path = str(abs_file_path.relative_to(plugin_root))
        except ValueError:
            # 如果文件不在插件根目录下（比如在 tools/ 子目录中），尝试从 tools 目录开始计算
            tools_dir = plugin_root / "tools"
            try:
                relative_path = str(abs_file_path.relative_to(tools_dir))
            except ValueError:
                # 如果还是不行，使用绝对路径
                relative_path = str(abs_file_path)
                self.console.print(f"  [yellow]⚠️ 警告: 无法计算相对路径，使用绝对路径: {relative_path}[/yellow]")

        # 4. 检查返回类型注解
        if 'return' not in hints:
            validation_warnings.append({
                "type": "return_annotation",
                "message": "方法缺少返回类型注解"
            })

        # 5. 检查文档字符串
        docstring = inspect.getdoc(method)
        if not docstring:
            validation_warnings.append({
                "type": "docstring",
                "message": "方法缺少文档字符串"
            })

        # 6. 检查异步标记
        if not inspect.iscoroutinefunction(method):
            validation_warnings.append({
                "type": "async_marker",
                "message": "考虑使用 async 定义异步方法"
            })

        # 如果有校验警告，打印出来
        if validation_warnings:
            self.console.print(f"  [yellow]⚠️ 代码规范警告 {class_name}.{m_name}:[/yellow]")
            for warning in validation_warnings:
                if warning["type"] == "parameter_annotation":
                    self.console.print(f"    [red]✗ 参数 '{warning['param']}' 应该使用 Annotated[str, \"描述\"] 格式[/red]")
                elif warning["type"] == "parameter_description":
                    self.console.print(f"    [red]✗ 参数 '{warning['param']}' 的 Annotated 注解缺少描述[/red]")
                elif warning["type"] == "return_annotation":
                    self.console.print(f"    [yellow]⚠ 缺少返回类型注解[/yellow]")
                elif warning["type"] == "docstring":
                    self.console.print(f"    [yellow]⚠ 缺少文档字符串[/yellow]")
                elif warning["type"] == "async_marker":
                    self.console.print(f"    [blue]ℹ 考虑使用 async 定义异步方法[/blue]")

        return {
            "name": m_name,
            "category": getattr(method, "_action_category", "exec"),
            "description": inspect.getdoc(method) or "",
            "location": {
                "file": relative_path,
                "class": class_name
            },
            "inputSchema": {
                "type": DataTypes.OBJECT,
                "properties": properties,
                "required": required
            },
            "outputSchema": output_res,
            "_validation_warnings": validation_warnings  # 新增：包含校验警告
        }

    def scan_tools_directory_smart(self, plugin_root: Path, intent: str = "default") -> List[Dict[str, Any]]:
        """
        智能扫描 tools 目录

        Args:
            plugin_root: 插件根目录
            intent: 扫描意图，可选值: default, strict, performance, security, cleanup

        Returns:
            Action 列表
        """
        tools_dir = plugin_root / "tools"

        if not tools_dir.exists():
            self.console.print(f"[yellow]⚠️ 警告: {tools_dir} 目录不存在[/yellow]")
            return []

        # 创建智能优化器
        optimizer = create_scanner_with_intent(self.console, intent)

        # 智能过滤文件
        self.console.print(f"[bold cyan]🔍 正在智能扫描 tools 目录 (模式: {intent})...[/bold cyan]")
        py_files = optimizer.filter_files(tools_dir, recursive=True)

        if not py_files:
            self.console.print("[yellow]⚠️ 警告: 未找到符合条件的Python文件[/yellow]")
            return []

        # 1. 检查全量缓存
        if self.use_cache and self.cache_mgr.is_cache_valid(plugin_root, py_files):
            cached_actions = self.cache_mgr.load_cache(plugin_root)
            if cached_actions:
                self.console.print("[green]✨ 使用缓存的扫描结果[/green]")
                return cached_actions

        # 2. 快速 AST 扫描获取签名
        all_actions = []

        # 使用多线程加速 AST 扫描
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(OptimizedASTScanner.extract_action_signatures, f): f
                for f in py_files
            }

            for future in futures:
                py_file = futures[future]
                try:
                    actions_sig = future.result()
                    for action_sig in actions_sig:
                        # 添加文件路径信息
                        action_sig["file_path"] = str(py_file)
                        all_actions.append(action_sig)
                        self.console.print(
                            f"  [green]✓[/green] {py_file.relative_to(plugin_root)}: "
                            f"{action_sig['class_name']}.{action_sig['name']}"
                        )
                except Exception as e:
                    self.console.print(f"  [red]✗ {py_file.name}: {e}[/red]")

        # 3. 对所有签名进行完整解析（需要类型信息）
        if all_actions:
            self.console.print("[bold cyan]⚙️ 正在解析类型信息...[/bold cyan]")
            full_actions = self._enrich_with_types(all_actions, plugin_root, py_files)
        else:
            full_actions = []
            self.console.print("[yellow]⚠️ 警告: 未扫描到任何有效的 Action[/yellow]")

        # 4. 保存缓存
        if self.use_cache and full_actions:
            self.cache_mgr.save_cache(plugin_root, full_actions)

        # 5. 提供优化建议
        if intent in ["default", "performance", "cleanup"]:
            suggestions = optimizer.get_optimization_suggestions(plugin_root)
            if suggestions:
                self.console.print("[bold yellow]💡 优化建议:[/bold yellow]")
                for suggestion in suggestions:
                    self.console.print(f"  • {suggestion}")

        return full_actions

    def analyze_code_quality(self, plugin_root: Path) -> Dict[str, Any]:
        """
        分析代码质量

        Args:
            plugin_root: 插件根目录

        Returns:
            质量分析报告
        """
        tools_dir = plugin_root / "tools"

        if not tools_dir.exists():
            return {"error": f"{tools_dir} 目录不存在"}

        optimizer = create_scanner_with_intent(self.console, "strict")
        py_files = optimizer.filter_files(tools_dir, recursive=True)

        analysis_report = {
            "total_files": len(py_files),
            "files_analyzed": 0,
            "issues_found": 0,
            "suggestions": [],
            "file_details": [],
            "overall_score": 100,
        }

        for py_file in py_files:
            file_analysis = optimizer.analyze_code_quality(py_file)
            analysis_report["file_details"].append(file_analysis)
            analysis_report["files_analyzed"] += 1
            analysis_report["issues_found"] += len(file_analysis.get("issues", []))
            analysis_report["overall_score"] = min(
                analysis_report["overall_score"],
                file_analysis.get("score", 100)
            )

            # 收集建议
            for suggestion in file_analysis.get("suggestions", []):
                if suggestion not in analysis_report["suggestions"]:
                    analysis_report["suggestions"].append(suggestion)

        # 计算平均分数
        if analysis_report["files_analyzed"] > 0:
            total_score = sum(f["score"] for f in analysis_report["file_details"])
            analysis_report["average_score"] = total_score / analysis_report["files_analyzed"]
        else:
            analysis_report["average_score"] = 0

        return analysis_report

    def clear_cache(self, plugin_root: Optional[Path] = None) -> None:
        """清除缓存"""
        if self.use_cache:
            self.cache_mgr.clear_cache(plugin_root)
        self._ast_cache.clear()

    # 向后兼容的简单扫描方法
    def scan_tools_directory_simple(self, plugin_root: Path) -> List[Dict[str, Any]]:
        """
        简单的扫描方法（向后兼容）

        Args:
            plugin_root: 插件根目录

        Returns:
            Action 列表
        """
        tools_dir = plugin_root / "tools"
        all_actions = []

        if not tools_dir.exists():
            return []

        py_files = list(tools_dir.rglob("*.py"))
        for py_file in py_files:
            if py_file.name.startswith("__"):
                continue

            # 显示扫描进度日志
            rel_path = py_file.relative_to(plugin_root)
            self.console.print(f"  [bold cyan]🔍 扫描文件:[/bold cyan] {rel_path}")

            actions = self._extract_actions_from_file(py_file, plugin_root)
            all_actions.extend(actions)

        return all_actions

    def _extract_actions_from_file(self, file_path: Path, plugin_root: Path) -> List[Dict[str, Any]]:
        """动态加载模块并解析类与方法"""
        actions = []
        abs_file_path = file_path.resolve()
        module_name = abs_file_path.stem

        # 将 tools 目录加入路径以支持内部导入
        tools_path = str(plugin_root / "tools")
        if tools_path not in sys.path:
            sys.path.insert(0, tools_path)

        try:
            spec = importlib.util.spec_from_file_location(module_name, str(abs_file_path))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for name, obj in inspect.getmembers(module):
                # 必须继承自 BasePlugin 且不是 BasePlugin 本身
                if inspect.isclass(obj) and issubclass(obj, BasePlugin) and obj is not BasePlugin:
                    self.console.print(f"    [green]found class:[/green] [bold]{name}[/bold]")

                    for m_name, method in inspect.getmembers(obj, predicate=inspect.isfunction):
                        if hasattr(method, "_is_action"):
                            # 提取逻辑
                            action_meta = self._parse_to_meta(m_name, method, name, abs_file_path, plugin_root)
                            actions.append(action_meta)

                            category = getattr(method, "_action_category", "exec")
                            icon = "⚙️" if category == "config" else "⚡"
                            self.console.print(f"      [green]-> extracted action:[/green] {icon} {m_name}")
        except Exception as e:
            self.console.print(f"    [red]❌ 加载失败 {file_path.name}: {str(e)}[/red]")
        finally:
            if tools_path in sys.path:
                sys.path.remove(tools_path)

        return actions

