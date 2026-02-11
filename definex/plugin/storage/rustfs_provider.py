import uuid
from typing import List

import definex_engine # Rust 核心
import polars as pl
from definex.plugin.storage.base import BaseStorageProvider

class RustFSProvider(BaseStorageProvider):
    def __init__(self):
        self.engine = definex_engine.RustFSDriver()

    def save_df(self, ctx, df: pl.DataFrame) -> str:
        # 路径规则：租户/Trace/Node/随机UUID -> 解决并发覆盖问题
        unique_id = uuid.uuid4().hex
        rel_path = f"{ctx.trace_id}/{ctx.node_id}/{unique_id}.parquet"

        # 调用 Rust 引擎执行零拷贝写入
        self.driver.write_parquet(df, rel_path)
        return f"dfx://rustfs/{rel_path}"

    def merge_df(self, ctx, uris: List[str]) -> str:
        # 分布式合并：在存储端执行元数据级合并
        target = f"{ctx.trace_id}/merged_{ctx.node_id}.parquet"
        keys = [u.replace("dfx://rustfs/", "") for u in uris]
        self.driver.concat(keys, target)
        return f"dfx://rustfs/{target}"

    def get_physical_path(self, uri: str):
        return self.engine.get_mmap_path(uri.replace("dfx://rustfs/", ""))