"""
DefineX 文件监控器
优化的事件处理和增量扫描机制
"""
import threading
import time
from collections import deque
from pathlib import Path
from typing import Set

from rich.panel import Panel
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class EventQueue:
    """事件队列，用于合并和处理文件系统事件"""

    def __init__(self, max_size: int = 100):
        self.queue = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._processed_files: Set[str] = set()
        self._last_process_time = 0
        self._cooldown = 0.5  # 冷却时间（秒）

    def add_event(self, file_path: str, event_type: str) -> None:
        """添加事件到队列"""
        with self._lock:
            current_time = time.time()

            # 检查冷却时间
            if current_time - self._last_process_time < self._cooldown:
                return

            # 去重：同一文件在短时间内只处理一次
            if file_path in self._processed_files:
                return

            self.queue.append((file_path, event_type, current_time))
            self._processed_files.add(file_path)

    def get_events(self) -> list:
        """获取所有待处理事件"""
        with self._lock:
            events = list(self.queue)
            self.queue.clear()
            self._processed_files.clear()
            self._last_process_time = time.time()
            return events

    def clear(self) -> None:
        """清空队列"""
        with self._lock:
            self.queue.clear()
            self._processed_files.clear()


class OptimizedFileHandler(FileSystemEventHandler):
    """优化的文件系统事件处理器"""

    def __init__(self, watcher, root_path: Path, event_queue: EventQueue):
        self.watcher = watcher
        self.root_path = root_path
        self.event_queue = event_queue
        self._last_batch_time = 0
        self._batch_interval = 1.0  # 批量处理间隔

    def on_modified(self, event) -> None:
        """处理文件修改事件"""
        if not event.is_directory and event.src_path.endswith(".py"):
            self._handle_file_event(event.src_path, "modified")

    def on_created(self, event) -> None:
        """处理文件创建事件"""
        if not event.is_directory and event.src_path.endswith(".py"):
            self._handle_file_event(event.src_path, "created")

    def on_deleted(self, event) -> None:
        """处理文件删除事件"""
        if not event.is_directory and event.src_path.endswith(".py"):
            self._handle_file_event(event.src_path, "deleted")

    def on_moved(self, event) -> None:
        """处理文件移动事件"""
        if not event.is_directory and event.src_path.endswith(".py"):
            self._handle_file_event(event.src_path, "moved")
        if not event.is_directory and event.dest_path.endswith(".py"):
            self._handle_file_event(event.dest_path, "created")

    def _handle_file_event(self, file_path: str, event_type: str) -> None:
        """处理文件事件"""
        # 转换为相对路径
        try:
            rel_path = Path(file_path).relative_to(self.root_path)
        except ValueError:
            return  # 文件不在监控范围内

        # 添加到事件队列
        self.event_queue.add_event(str(rel_path), event_type)

        # 检查是否需要批量处理
        current_time = time.time()
        if current_time - self._last_batch_time >= self._batch_interval:
            self._process_batch()
            self._last_batch_time = current_time

    def _process_batch(self) -> None:
        """批量处理事件"""
        events = self.event_queue.get_events()
        if events:
            changed_files = [e[0] for e in events]
            if changed_files:
                self.watcher._trigger_incremental_sync(self.root_path, changed_files)


class PluginWatcher:
    """优化的插件监控器"""

    def __init__(self, console, generator, validator, scanner):
        """
        console: Rich Console 实例
        generator: ManifestGenerator 实例 (负责同步 YAML)
        validator: ProjectValidator 实例 (负责合规检查)
        scanner: CodeScanner 实例 (负责增量扫描)
        """
        self.console = console
        self.generator = generator
        self.validator = validator
        self.scanner = scanner
        self.observer = None
        self.event_queue = EventQueue()
        self._is_running = False

    def start_watching(self, path: str) -> None:
        """启动持续监听工作流"""
        root = Path(path).resolve()
        tools_path = root / "tools"

        # 检查 tools 目录是否存在
        if not tools_path.exists():
            self.console.print(f"[red]❌ 错误: 找不到 tools 目录 ({tools_path})[/red]")
            return

        # 界面初始化展示
        self.console.clear()
        self.console.print(Panel(
            f"[bold green]DefineX 哨兵模式 (Watch Mode) 已就绪[/bold green]\n"
            f"📍 监控路径: [cyan]{tools_path}[/cyan]\n"
            f"🔄 自动化流: [yellow]增量扫描[/yellow] -> [yellow]Manifest 同步[/yellow] -> [yellow]契约校验[/yellow]\n"
            f"⚡ 优化特性: 事件批量处理、增量扫描、智能去重",
            title="[bold white]Service Status[/bold white]",
            expand=False
        ))

        # 初始执行一次完整检查
        self._trigger_full_sync(root, "Initial Startup")

        # 设置并启动监听
        self.observer = Observer()
        handler = OptimizedFileHandler(self, root, self.event_queue)
        self.observer.schedule(handler, str(tools_path), recursive=True)

        self._is_running = True

        try:
            self.observer.start()
            self.console.print("\n[bold cyan]👀 持续监听中...[/bold cyan] [dim](按下 Ctrl+C 停止服务)[/dim]")

            # 主循环，定期检查事件队列
            while self._is_running:
                time.sleep(0.5)  # 更短的睡眠时间，提高响应性
                # 定期处理队列中的事件
                events = self.event_queue.get_events()
                if events:
                    changed_files = [e[0] for e in events]
                    self._trigger_incremental_sync(root, changed_files)

        except KeyboardInterrupt:
            self.stop()
            self.console.print("\n[yellow]👋 已停止代码监听服务。[/yellow]")
        except Exception as e:
            self.console.print(f"[bold red]❌ 监听引擎异常: {e}[/bold red]")
            self.stop()

        if self.observer:
            self.observer.join()

    def stop(self) -> None:
        """停止监控"""
        self._is_running = False
        if self.observer:
            self.observer.stop()
            self.observer = None

    def _trigger_full_sync(self, root: Path, trigger_reason: str) -> None:
        """执行完整的同步与检查"""
        self.console.clear()
        self.console.print(f"[bold yellow]🔔 全量同步:[/bold yellow] {trigger_reason}")
        self.console.print(f"[dim]刷新时间: {time.strftime('%H:%M:%S')}[/dim]\n")

        try:
            # 第一步：运行扫描器并生成/合并 manifest.yaml
            self.generator.generate(root)

            # 第二步：运行全量合规性检查
            is_valid = self.validator.check_all(root)

            if is_valid:
                self.console.print(f"\n[bold green]✅ 契约对齐成功！当前代码状态完美。[/bold green]")
            else:
                self.console.print(f"\n[bold red]🚨 契约不一致！请查看上方红色报错并修正 tools/ 中的代码。[/bold red]")

        except Exception as e:
            self.console.print(f"[bold red]❌ 自动化流程执行中断: {e}[/bold red]")

        self._print_status()

    def _trigger_incremental_sync(self, root: Path, changed_files: list) -> None:
        """执行增量同步与检查"""
        if not changed_files:
            return

        self.console.clear()
        self.console.print(f"[bold yellow]🔔 增量同步:[/bold yellow] {len(changed_files)} 个文件变更")
        self.console.print(f"[dim]变更文件: {', '.join(changed_files[:3])}{'...' if len(changed_files) > 3 else ''}[/dim]")
        self.console.print(f"[dim]刷新时间: {time.strftime('%H:%M:%S')}[/dim]\n")

        try:
            # 第一步：运行增量扫描器并生成/合并 manifest.yaml
            # 注意：这里需要修改generator以支持增量生成
            self.generator.generate(root)  # 暂时使用全量生成

            # 第二步：运行增量合规性检查
            # 注意：这里需要修改validator以支持增量检查
            is_valid = self.validator.check_all(root)  # 暂时使用全量检查

            if is_valid:
                self.console.print(f"\n[bold green]✅ 契约对齐成功！变更已同步。[/bold green]")
            else:
                self.console.print(f"\n[bold red]🚨 契约不一致！请查看上方红色报错。[/bold red]")

        except Exception as e:
            self.console.print(f"[bold red]❌ 增量流程执行中断: {e}[/bold red]")

        self._print_status()

    def _print_status(self) -> None:
        """打印状态信息"""
        self.console.print("\n[bold cyan]👀 持续监听中...[/bold cyan] [dim](按下 Ctrl+C 停止服务)[/dim]")
