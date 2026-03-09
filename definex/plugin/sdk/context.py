import os
import psutil
import time
import threading
from typing import Dict, Any, Callable
from definex.plugin.sdk.events import ActionEvent, ActionEventType
from definex.plugin.sdk.collector import RealtimeCollector

class ActionContext:
    def __init__(self,
                 trace_id: str,
                 node_id: str,
                 stop_event: Any,
                 storage_service: Any,
                 event_bus: Callable[[dict], None],
                 env_vars: Dict[str, str] = None):

        self.trace_id = trace_id
        self.node_id = node_id
        self._stop_event = stop_event
        self._event_bus = event_bus
        self.env = env_vars or {}

        # 1. 基础资源审计初始化
        self._process = psutil.Process(os.getpid())
        self._start_time = time.perf_counter()

        # 记录初始快照 (用于计算增量)
        init_mem = self._process.memory_info()
        self._initial_rss = init_mem.rss
        self._peak_rss = self._initial_rss

        try:
            init_io = self._process.io_counters()
            self._initial_read_bytes = init_io.read_bytes
            self._initial_write_bytes = init_io.write_bytes
        except (AttributeError, Exception):
            self._initial_read_bytes = self._initial_write_bytes = 0

        # 2. 业务度量初始化
        self.rows_processed = 0
        self.spill_count = 0

        # 3. 关联实时数据收集器
        self.collector = RealtimeCollector(self, storage_service)

        # 4. 启动后台资源监控线程 (捕获内存峰值)
        self._monitor_active = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    # --- 后台监控逻辑 ---
    def _monitor_loop(self):
        """每 100ms 采样一次内存峰值"""
        while self._monitor_active:
            try:
                curr_rss = self._process.memory_info().rss
                if curr_rss > self._peak_rss:
                    self._peak_rss = curr_rss
                time.sleep(0.1)
            except (psutil.NoSuchProcess, Exception):
                break

    # --- 核心事件发射接口 ---
    def emit(self, event_type: ActionEventType, message: str = "", data: Any = None):
        """安全地向系统总线发送生命周期事件"""
        try:
            event = ActionEvent(event_type, self.trace_id, self.node_id, message, data)
            self._event_bus(event.to_dict())
        except Exception as e:
            # 监控事件失败不应阻断业务逻辑
            print(f"[DefineX Context] Failed to emit event {event_type}: {e}")

    def report_progress(self, percent: float, message: str = ""):
        """业务层调用的进度汇报"""
        self.emit(ActionEventType.PROGRESS, message, {"percent": percent})

    def record_data_metrics(self, rows: int = 0, spills: int = 0):
        """手动记录数据处理度量"""
        self.rows_processed += rows
        self.spill_count += spills

    def check_cancelled(self):
        """检查中断信号"""
        if self._stop_event.is_set():
            self.emit(ActionEventType.CANCELLED, "Task interrupted by user")
            # 停止监控
            self._monitor_active = False
            raise InterruptedError("DefineX Action Cancelled")

    # --- 最终指标生成 ---
    def capture_metrics(self) -> Dict[str, Any]:
        """执行结束时调用：生成全量性能与业务画像"""
        self._monitor_active = False # 停止监控线程

        end_time = time.perf_counter()
        duration_ms = (end_time - self._start_time) * 1000

        final_mem = self._process.memory_info()

        # 计算 IO 增量
        try:
            final_io = self._process.io_counters()
            read_inc = final_io.read_bytes - self._initial_read_bytes
            write_inc = final_io.write_bytes - self._initial_write_bytes
        except:
            read_inc = write_inc = 0

        return {
            "performance": {
                "duration_ms": round(duration_ms, 2),
                "memory": {
                    "start_mb": round(self._initial_rss / 1024 / 1024, 2),
                    "peak_mb": round(self._peak_rss / 1024 / 1024, 2),
                    "end_mb": round(final_mem.rss / 1024 / 1024, 2),
                    "delta_mb": round((final_mem.rss - self._initial_rss) / 1024 / 1024, 2)
                },
                "cpu_utilization": self._process.cpu_percent(),
                "io": {
                    "read_bytes": read_inc,
                    "write_bytes": write_inc
                }
            },
            "data_ops": {
                "rows_processed": self.rows_processed,
                "spill_events": self.spill_count
            }
        }

    # --- Python Context Manager 支持 ---
    def __enter__(self):
        self.emit(ActionEventType.ENTER, "Executing business logic")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 确保监控线程关闭
        self._monitor_active = False

        if exc_type:
            if issubclass(exc_type, InterruptedError):
                # 信号已由 check_cancelled 处理
                pass
            else:
                self.emit(ActionEventType.EXCEPTION, f"Runtime Error: {str(exc_val)}", {
                    "error_type": exc_type.__name__
                })
        else:
            # 任务成功结束，采集并上报最终指标
            metrics = self.capture_metrics()
            self.emit(ActionEventType.SUCCESS, "Action finished successfully", metrics)