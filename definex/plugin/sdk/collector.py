import polars as pl
from typing import List, Any, Dict
from definex.plugin.sdk.policy import ResourcePolicy
from definex.plugin.sdk.events import ActionEventType

class RealtimeCollector:
    def __init__(self, context, storage_service):
        self._ctx = context
        self._storage = storage_service
        self._buffer: List[Dict] = []
        self._current_buffer_bytes = 0
        self._spilled_parts: List[str] = [] # 存储已溢写的分片 URI
        self._is_active = False

    def add(self, row: Dict[str, Any]):
        """插件调用：实时添加数据行"""
        self._buffer.append(row)
        self._current_buffer_bytes += ResourcePolicy.estimate_row_size(row)
        self._is_active = True

        # 触发判断：字节数超限 或 行数达到 Group 限制
        if (self._current_buffer_bytes >= ResourcePolicy.AUTO_SPILL_THRESHOLD_BYTES or
                len(self._buffer) >= ResourcePolicy.ROW_GROUP_SIZE):
            self._spill_to_disk()

    def _spill_to_disk(self):
        """[核心] 执行物理溢写，清空内存"""
        if not self._buffer:
            return

        # 发送 SPILL 事件，通知前端和监控
        self._ctx.emit(
            ActionEventType.SPILL,
            message=f"Memory threshold hit ({len(self._buffer)} rows), spilling to RustFS..."
        )

        # 1. 转化为 Polars 内存视图 (Arrow 布局)
        df = pl.from_dicts(self._buffer)

        # 2. 调用存储服务保存为 Parquet 分片
        # 这里的 storage_service 会生成一个 dfx://rustfs/... 的地址
        part_uri = self._storage.save_temp_batch(df, self._ctx.trace_id)
        self._spilled_parts.append(part_uri)

        # 3. 彻底释放 Python 堆内存引用
        self._buffer = []
        self._current_buffer_bytes = 0

    def get_result(self) -> Dict[str, Any]:
        """Action 结束时调用：汇总结果"""
        # 如果从未使用过 collector (即插件直接返回了简单对象)
        if not self._is_active:
            return None

        # 如果发生过溢写，或者 buffer 里还有残余数据
        if self._spilled_parts or self._buffer:
            # A. 处理最后的残余数据
            if self._buffer:
                self._spill_to_disk()

            # B. 逻辑合并：调用 RustFS 进行元数据层面的物理合并
            # 不加载回内存，而是生成一个新的指向完整数据集的 URI
            final_uri = self._storage.merge_parts(
                self._spilled_parts,
                target_id=f"final_{self._ctx.node_id}_{self._ctx.trace_id}"
            )

            return {
                "uri": final_uri,
                "is_ref": True,
                "type": "dataframe",
                "metrics": {
                    "total_parts": len(self._spilled_parts),
                    "storage": "rustfs"
                }
            }
        return []

    def is_active(self):
        return self._is_active