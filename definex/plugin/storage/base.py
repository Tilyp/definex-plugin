from abc import ABC, abstractmethod
import polars as pl
from typing import List

class BaseStorageProvider(ABC):
    @abstractmethod
    def save_batch(self, df: pl.DataFrame, trace_id: str) -> str:
        """保存数据分片并返回 URI"""
        pass

    @abstractmethod
    def merge_parts(self, uris: List[str], target_id: str) -> str:
        """合并多个分片"""
        pass

    @abstractmethod
    def get_physical_path(self, uri: str) -> str:
        """获取本地映射路径或下载后的路径"""
        pass

    @abstractmethod
    def delete(self, uri: str):
        """物理删除资源"""
        pass