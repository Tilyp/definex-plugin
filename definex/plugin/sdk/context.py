import os
import psutil
import time
from typing import Dict, Any, Callable
from definex.plugin.sdk.events import ActionEvent, ActionEventType
from definex.plugin.sdk.collector import RealtimeCollector


class TracingInfo:
    def __init__(self, trace_id: str):
        self.trace_id = trace_id

class ActionContext:
    def __init__(self,
                 trace_id: str,
                 node_id: str,
                 stop_event: Any,
                 storage_service: Any,
                 event_bus: Callable[[dict], None], # 通常是传往 Valkey 的函数
                 env_vars: Dict[str, str] = None):

        self.trace_id = trace_id
        self.node_id = node_id
        self._stop_event = stop_event
        self._event_bus = event_bus
        self.env = env_vars or {}

        # 关联实时数据收集器 (处理 5MB 溢写逻辑)
        self.collector = RealtimeCollector(self, storage_service)

        # 资源审计起效
        self._process = psutil.Process(os.getpid())
        self._start_time = time.perf_counter()
        self._initial_rss = self._process.memory_info().rss

    # --- 核心事件发射接口 ---
    def emit(self, event_type: ActionEventType, message: str = "", data: Any = None):
        """向系统总线发送生命周期事件"""
        event = ActionEvent(event_type, self.trace_id, self.node_id, message, data)
        # 通过 Valkey Pub/Sub 实时推送到控制面
        self._event_bus(event.to_dict())

    def report_progress(self, percent: float, message: str = ""):
        """业务层调用的进度汇报"""
        self.emit(ActionEventType.PROGRESS, message, {"percent": percent})

    def check_cancelled(self):
        """检查中断信号"""
        if self._stop_event.is_set():
            self.emit(ActionEventType.CANCELLED, "Task interrupted by user")
            raise InterruptedError("DefineX Action Cancelled")

    # --- 资源与度量 ---
    def get_resource_usage(self) -> dict:
        """获取当前进程的资源快照"""
        mem_info = self._process.memory_info()
        return {
            "duration_ms": (time.perf_counter() - self._start_time) * 1000,
            "memory_rss_mb": mem_info.rss / 1024 / 1024,
            "memory_delta_mb": (mem_info.rss - self._initial_rss) / 1024 / 1024,
            "cpu_percent": self._process.cpu_percent()
        }

    # --- Python Context Manager 支持 --
    def __enter__(self):
        """支持 with context: 语法，自动发送进入事件"""
        self.emit(ActionEventType.ENTER, "Executing business logic")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """自动处理结束与异常事件"""
        if exc_type:
            if issubclass(exc_type, InterruptedError):
                # 已由 check_cancelled 发送
                pass
            else:
                self.emit(ActionEventType.EXCEPTION, f"Runtime Error: {str(exc_val)}", {
                    "error_type": exc_type.__name__
                })
        else:
            metrics = self.get_resource_usage()
            self.emit(ActionEventType.SUCCESS, "Action finished successfully", metrics)