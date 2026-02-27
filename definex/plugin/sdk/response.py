import uuid
from typing import Any, Optional, Dict
from pathlib import Path

# 内部依赖
from .policy import ResourcePolicy

class ActionResponse:
    """
    DefineX 标准响应封装类
    职责：
    1. 统一输出格式 (status, data, message, metadata)
    2. 深度递归序列化 (支持自定义类、列表、字典)
    3. 自适应溢写逻辑 (当 data 过大时自动转为 dfx:// 引用)
    """

    def __init__(self,
                 status: str = "success",
                 data: Any = None,
                 message: str = "",
                 error_code: Optional[int] = None,
                 trace_context: Any = None):
        self.status = status        # "success" 或 "error"
        self.data = data            # 业务数据载荷
        self.message = message      # 执行摘要（供 AI 和前端展示）
        self.error_code = error_code # 错误码（可选）

        # 审计元数据（自动从 context 中提取或在运行中更新）
        self.metadata = {
            "trace_id": getattr(trace_context, "trace_id", None),
            "node_id": getattr(trace_context, "node_id", None),
            "performance": {},      # 耗时、内存占用等
            "data_info": {
                "is_ref": False,    # 是否已转为 URI 引用
                "type": None        # 数据语义类型 (dataframe, image, etc.)
            }
        }

    @classmethod
    def success(cls, data: Any = None, message: str = "Operation successful", ctx: Any = None):
        """便捷成功工厂方法"""
        return cls(status="success", data=data, message=message, trace_context=ctx)

    @classmethod
    def error(cls, message: str, error_code: int = 500, data: Any = None, ctx: Any = None):
        """便捷失败工厂方法"""
        return cls(status="error", message=message, error_code=error_code, data=data, trace_context=ctx)

    def finalize(self, storage_provider=None) -> Dict[str, Any]:
        """
        [核心逻辑] 响应最终化处理：
        1. 检查数据体积，决定是否进行自适应溢写
        2. 补全性能度量指标
        3. 执行最终序列化
        """
        # 1. 检查是否已经是引用 (如果是 TabularData 等类型，标记 type)
        if hasattr(self.data, 'is_ref') and self.data.is_ref:
            self.metadata["data_info"]["is_ref"] = True

        # 2. 自动溢写判断：如果 data 是大型容器且未被标记为引用
        if self.status == "success" and not self.metadata["data_info"]["is_ref"]:
            if ResourcePolicy.should_spill(self.data):
                self._spill_data(storage_provider)

        # 3. 递归序列化返回字典
        return self.to_dict()

    def _spill_data(self, storage_provider):
        """
        内部逻辑：将内存对象转化为分布式引用
        """
        if not storage_provider:
            return # 无存储服务时保持内存状态

        import polars as pl
        try:
            # 自动探测并转化
            if isinstance(self.data, list):
                df = pl.from_dicts(self.data)
            elif isinstance(self.data, dict):
                df = pl.from_dict(self.data)
            else:
                return # 无法转换的非结构化数据

            # 执行物理写入 (RustFS/S3)
            file_id = f"res_{uuid.uuid4().hex}.parquet"
            uri = storage_provider.save_parquet(df, file_id)

            # 更新数据为引用格式
            self.data = {
                "uri": uri,
                "is_ref": True,
                "row_count": len(df),
                "type": "dataframe"
            }
            self.metadata["data_info"].update({
                "is_ref": True,
                "type": "dataframe"
            })
            self.message += " (Payload exceeded 5MB: auto-spilled to storage)"

        except Exception as e:
            self.message += f" [Spill Failed: {str(e)}]"

    def to_dict(self) -> Dict[str, Any]:
        """
        全量深度序列化
        """
        return {
            "status": self.status,
            "message": self.message,
            "error_code": self.error_code,
            "data": self._serialize(self.data),
            "metadata": self._serialize(self.metadata)
        }

    def _serialize(self, obj: Any) -> Any:
        """
        递归序列化引擎：处理 Dict, List, Class, Enum
        """
        if isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize(i) for i in obj]
        elif hasattr(obj, "to_dict"): # 优先调用自定义序列化
            return obj.to_dict()
        elif hasattr(obj, "__dict__"):
            # 将自定义 POJO 类实例转为字典
            return {k: self._serialize(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
        elif isinstance(obj, (Path)):
            return str(obj)
        # 基础类型直接返回
        return obj

    def __repr__(self):
        return f"<ActionResponse status={self.status} is_ref={self.metadata['data_info']['is_ref']}>"