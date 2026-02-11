import os

class ResourcePolicy:
    # 默认 5MB 触发溢写，可通过环境变量动态调整
    AUTO_SPILL_THRESHOLD_BYTES = int(os.getenv("DFX_MEMORY_THRESHOLD_BYTES", 5 * 1024 * 1024))

    # 强制分片行数（例如每 10 万行强制写一次盘，防止单行过大）
    ROW_GROUP_SIZE = int(os.getenv("DFX_ROW_GROUP_SIZE", 100000))

    @staticmethod
    def estimate_row_size(row: dict) -> int:
        """估算单行字典的内存占用"""
        import sys
        # 基础字典结构开销 + 键值对预估
        return sys.getsizeof(row) + sum(sys.getsizeof(k) + sys.getsizeof(v) for k, v in row.items())