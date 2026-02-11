import uuid
from multiprocessing import shared_memory
from typing import List
import polars as pl
from definex.plugin.storage.base import BaseStorageProvider
from plugin.sdk import ActionContext


class MemoryProvider(BaseStorageProvider):

    def delete(self, uri: str):
        pass

    def save_batch(self, ctx: ActionContext, df: pl.DataFrame) -> str:
        # 利用 trace_id 命名，支持同任务多节点并发
        shm_name = f"dfx_{ctx.trace_id}_{ctx.node_id}_{uuid.uuid4().hex}"
        buf = df.to_arrow().to_batches()[0].to_pybytes() # 简化
        shm = shared_memory.SharedMemory(create=True, size=len(buf), name=shm_name)
        shm.buf[:] = buf
        return f"dfx://shm/{shm_name}?size={len(buf)}"

    def merge_parts(self, uris: List[str], target_id: str) -> str:
        # 内存模式下的合并通常是逻辑上的，这里简化为重新分配大块内存
        # 实际大数据 ETL 建议降级为 RustFS/Ceph
        return uris[0]

    def get_physical_path(self, uri: str):
        return uri # 内存模式直接返回 URI，由 Runtime 解析为内存指针