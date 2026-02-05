from definex.plugin.sdk.collector import RealtimeCollector

class TracingInfo:
    def __init__(self, trace_id: str):
        self.trace_id = trace_id

class ActionContext:
    def __init__(self, tracing: TracingInfo, storage):
        self.tracing = tracing
        self.env = {}
        self.collector = RealtimeCollector(self, storage)

    def report_progress(self, percent: float = 0, msg: str = ""):
        # 实际通过消息队列发送进度
        print(f"[{self.tracing.trace_id}] {percent}% : {msg}")