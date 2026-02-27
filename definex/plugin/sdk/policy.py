import json
import os
import sys


class ResourcePolicy:
    # 默认 5MB 触发溢写，可通过环境变量动态调整
    AUTO_SPILL_THRESHOLD_BYTES = int(os.getenv("DFX_MEMORY_THRESHOLD_BYTES", 5 * 1024 * 1024))

    # 强制分片行数（例如每 10 万行强制写一次盘，防止单行过大）
    ROW_GROUP_SIZE = int(os.getenv("DFX_ROW_GROUP_SIZE", 100000))

    @staticmethod
    def estimate_size(obj) -> int:
        """精准估算对象内存占用"""
        if obj is None: return 0
        try:
            if isinstance(obj, (list, dict)):
                # 序列化估算法最为接近网络传输体积
                return len(json.dumps(obj, ensure_ascii=False))
            return sys.getsizeof(obj)
        except:
            return sys.getsizeof(obj)

    @staticmethod
    def should_spill(data) -> bool:
        """判断数据是否达到了溢写红线"""
        if data is None: return False
        # 仅对集合类数据进行溢写判断
        if isinstance(data, (list, dict)):
            return ResourcePolicy.estimate_size(data) > ResourcePolicy.AUTO_SPILL_THRESHOLD_BYTES
        return False