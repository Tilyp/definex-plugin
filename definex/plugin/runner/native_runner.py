"""
DefineX 原生运行器 - 专门处理原生模式执行逻辑
从 PluginRunner 中提取的业务逻辑
"""

import json
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from definex.plugin.core.console_utils import ConsoleFactory
from definex.plugin.runner.param_validate import ParamsValidate
from definex.plugin.runtime import PluginRuntime
from definex.plugin.sdk import ActionContext


class NativeRunner:
    """原生运行器 - 专门处理原生模式的执行逻辑"""

    def __init__(self, console: Console, plugin_runtime: PluginRuntime):
        """
        初始化原生运行器

        Args:
            console: 控制台输出
            manifest_gen: 契约生成器
        """
        self.console = console
        self.plugin_runtime = plugin_runtime
        self.params_validate = ParamsValidate()

    def run(self,action: Optional[str] = None,
            params_json: Optional[str] = None, watch: bool = False,
            repl: bool = False, debug: bool = False, context: ActionContext = None) -> Any:
        """
        执行原生模式运行

        Args:
            action: 指定执行的action
            params_json: 参数JSON字符串
            watch: 是否监控
            repl: 是否交互模式
            debug: 是否调试模式
            context: 任务上下文

        Returns:
            运行结果
        """
        if repl:
            return self._run_native_interactive(debug, context)
        else:
            return self._run_native_single(action, params_json, watch, context)

    def _run_native_single(self, action: str, params_json: str, watch: bool, context: ActionContext):
        """执行单次运行"""
        def _exec():
            action_meta = self.plugin_runtime.get_action_metadata(action)
            if action_meta is None:
                msg = f"未找到action[{action}],请核对后再访问"
                self._print_error(msg, True)
            else:
                # 解析参数
                params = {}
                if params_json:
                    try:
                        params = json.loads(params_json)
                        self.params_validate.validate(params, action_meta['inputSchema'])
                    except json.JSONDecodeError as e:
                        self.console.print(f"[red]❌ JSON参数解析失败: {e}[/red]")
                        return
                is_streaming = action_meta.get("is_streaming", False)
                if is_streaming:
                    self.console.print(f"[bold blue]实时流输出:[/bold blue]")
                    for chunk in self.plugin_runtime.execute_stream(action_meta, params, context):
                        # 1. 人机交互模式：实时打印 delta
                        print(chunk["delta"], end="", flush=True)
                    print("\n")
                else:
                    try:
                        result = self.plugin_runtime.execute(action_meta, params, context)
                        self._print_success(result, is_machine=False)
                        return result
                    except Exception as e:
                        self._print_error(e, is_machine=False)
                        raise
        if watch:
            self._start_watcher(_exec)
        else:
            return _exec()

    def _run_native_interactive(self, is_debug: bool, context: ActionContext):
        """执行交互式运行"""
        # 具体的交互逻辑（从原PluginRunner中提取）
        console_factory = ConsoleFactory()
        machine_mode = console_factory.is_machine_mode()
        actions = self.plugin_runtime.actions
        plugin_name = self.plugin_runtime.manifest["name"]

        self.console.print(Panel(
            f"[bold cyan]🔧 交互式插件执行器[/bold cyan]\n"
            f"插件: {plugin_name}\n"
            f"可用Action数: {len(actions)}",
            border_style="cyan"
        ))

        # 交互循环逻辑
        while True:
            try:
                line = input("> " if not machine_mode else "").strip()
                if not line:
                    continue

                if line.lower() in ["exit", "quit", "q"]:
                    break

                self._process_line(line, is_debug, context)
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[yellow]👋 退出交互模式[/yellow]")
                break
            except Exception as e:
                self._print_error(e, machine_mode)

    def _process_line(self, line: str, is_debug: bool, context: ActionContext):
        """处理输入行"""
        # 解析命令
        parts = line.split()
        if not parts:
            return
        command = parts[0].lower()

        if command == "list":
            # 列出所有action
            self.console.print("[bold cyan]可用Action列表:[/bold cyan]")
            for i, action in enumerate(self.plugin_runtime.actions, 1):
                self.console.print(f"  {i}. {action['name']} - {action.get('description', '无描述')}")

        elif command == "run":
            # 执行action
            if len(parts) < 2:
                self.console.print("[red]❌ 用法: run <action_name> [参数JSON][/red]")
                return

            action_name = parts[1]
            params_json = " ".join(parts[2:]) if len(parts) > 2 else "{}"
            action_meta = self.plugin_runtime.get_action_metadata(action_name)

            try:
                params = json.loads(params_json) if params_json else {}
                self.params_validate.validate(params, action_meta['inputSchema'])
            except json.JSONDecodeError as e:
                self.console.print(f"[red]❌ JSON参数解析失败: {e}[/red]")
                return

            try:
                is_streaming = action_meta.get("is_streaming", False)
                if is_streaming:
                    self.console.print(f"[bold blue]实时流输出:[/bold blue]")
                    for chunk in self.plugin_runtime.execute_stream(action_meta, params, context):
                        # 1. 人机交互模式：实时打印 delta
                        print(chunk["delta"], end="", flush=True)
                    print("\n")
                else:
                    result = self.plugin_runtime.execute(action_meta, params, context)
                    self._print_success(result, is_machine=False)
            except Exception as e:
                self._print_error(e, is_machine=False)

        elif command == "help":
            self.console.print("[bold cyan]可用命令:[/bold cyan]")
            self.console.print("  list - 列出所有action")
            self.console.print("  run <action> [params] - 执行action")
            self.console.print("  exit/quit/q - 退出")
            self.console.print("  help - 显示帮助")

        else:
            self.console.print(f"[red]❌ 未知命令: {command}[/red]")
            self.console.print("输入 'help' 查看可用命令")

    def _print_success(self, data, is_machine: bool):
        """打印成功结果"""
        if is_machine:
            print(json.dumps({"success": True, "data": data}, ensure_ascii=False))
        else:
            self.console.print(f"[green]✅ 执行成功[/green]")
            if data:
                self.console.print(f"结果: {data}")

    def _print_error(self, e, is_machine: bool):
        """打印错误信息"""
        if is_machine:
            result = {"success": False, "error": str(e)}
            print(json.dumps(result, ensure_ascii=False))
        else:
            self.console.print(f"[red]❌ 执行失败: {e}[/red]")

    def _start_watcher(self, callback):
        """启动文件监控"""
        class ChangeHandler(FileSystemEventHandler):
            def on_modified(self, event):
                if not event.is_directory and event.src_path.endswith('.py'):
                    callback()

        event_handler = ChangeHandler()
        observer = Observer()
        observer.schedule(event_handler, str(self.plugin_runtime.plugin_root), recursive=True)
        observer.start()

        try:
            self.console.print("[yellow]👀 监控文件变化中... (Ctrl+C退出)[/yellow]")
            callback()  # 首次执行
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

