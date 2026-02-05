from typing import Any, Optional, Dict


class ActionResponse:
    """
    DefineX Action 标准返回封装类
    """
    def __init__(self,
                 status: str = "success",
                 data: Any = None,
                 message: str = "",
                 error_code: Optional[int] = None):
        self.status = status         # "success" 或 "error"
        self.data = data             # 实际的业务数据对象 (符合自定义类定义)
        self.message = message       # 提示消息
        self.error_code = error_code # 错误码 (可选)

    @classmethod
    def success(cls, data: Any = None, message: str = "Operation successful"):
        """便捷成功工厂方法"""
        return cls(status="success", data=data, message=message)

    @classmethod
    def error(cls, message: str, error_code: int = 500, data: Any = None):
        """便捷失败工厂方法"""
        return cls(status="error", message=message, error_code=error_code, data=data)

    def to_dict(self) -> Dict[str, Any]:
        """
        深度序列化函数
        将对象及其嵌套的自定义类全部转换为原生的 Python 字典/列表结构
        """
        return self._serialize(self.__dict__)

    def _serialize(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize(i) for i in obj]
        elif hasattr(obj, "__dict__"):
            # 处理自定义类实例
            return {k: self._serialize(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
        else:
            # 基础类型直接返回
            return obj