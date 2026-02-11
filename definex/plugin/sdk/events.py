from enum import Enum
from typing import Any
import time

class ActionEventType(Enum):
    STARTED = "started"       # Sidecar 进程启动
    ENV_LOADED = "env_loaded" # 依赖库(libs/)注入完成
    ENTER = "enter"           # 进入业务函数执行
    PROGRESS = "progress"     # 业务进度汇报
    SPILL = "spill"           # 触发自适应溢写 (Memory -> RustFS)
    EXCEPTION = "exception"   # 运行异常
    SUCCESS = "success"       # 正常结束
    CANCELLED = "cancelled"   # 被用户手动中断

class ActionEvent:
    def __init__(self, event_type: ActionEventType, trace_id: str, node_id: str,
                 message: str = "", data: Any = None):
        self.event_type = event_type.value
        self.trace_id = trace_id
        self.node_id = node_id
        self.message = message
        self.data = data
        self.timestamp = time.time()

    def to_dict(self):
        return self.__dict__