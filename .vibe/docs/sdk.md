# SDK 设计

## 开发者接口

### 1. 基础类

```python
from definex.plugin.sdk import BasePlugin, action, DataTypes

class MyPlugin(BasePlugin):
    """插件主类，必须继承 BasePlugin"""
    pass
```

### 2. Action 装饰器

```python
@action(category: str = "exec", stream: bool = False)
```

**参数:**
- `category`: 分类 (exec/config/query/transform)
- `stream`: 是否流式响应

### 3. 类型定义

```python
from definex.plugin.sdk import DataTypes
# STRING, NUMBER, BOOLEAN, ARRAY, OBJECT, BLOB, NULL
```

### 4. 上下文

```python
from definex.plugin.sdk import ActionContext

class MyPlugin(BasePlugin):
    def my_action(self, ctx: ActionContext, 
                  name: Annotated[str, "姓名"]) -> str:
        
        # 检查取消
        ctx.check_cancelled()
        
        # 进度汇报
        ctx.report_progress(50.0, "处理中...")
        
        # 记录指标
        ctx.record_data_metrics(rows=100)
        
        # 发射事件
        ctx.emit(ActionEventType.PROGRESS, "完成", {...})
        
        return f"Hello, {name}"
```

### 5. 流式响应

```python
from definex.plugin.sdk import StreamChunk

@action(stream=True)
def stream_data(self, items: Annotated[List[str], "数据项"]):
    for i, item in enumerate(items):
        yield StreamChunk(
            delta=item,
            index=i,
            is_last=(i == len(items) - 1)
        )
```

### 6. 响应封装

```python
from definex.plugin.sdk import ActionResponse

def my_action(self) -> ActionResponse:
    return ActionResponse.success(data={...})
```

## SDK 导出

```python
# definex/plugin/sdk/__init__.py

__all__ = [
    "BasePlugin",        # 插件基类
    "action",           # 装饰器
    "ActionContext",    # 执行上下文
    "ActionResponse",   # 响应封装
    "DataTypes",        # 类型常量
    "ResourcePolicy",   # 资源策略
    "UI",               # UI 组件
    "TabularData",      # 表格数据
    "Image",            # 图片数据
    "MAX_NESTING_DEPTH", # 最大嵌套深度 (3)
    "StreamChunk",      # 流式块
    "COLLECTION_TYPES", # 集合类型
    "PYTHON_TO_SYSTEM_MAP", # 类型映射
]
```

## 使用示例

```python
# tools/main.py

from typing import Annotated, List
from definex.plugin.sdk import BasePlugin, action, DataTypes

class DataProcessor(BasePlugin):
    """数据处理器插件"""
    
    @action(category="transform")
    def process_items(
        self,
        items: Annotated[List[str], "待处理的数据项"],
        mode: Annotated[str, "处理模式"] = "default"
    ) -> Annotated[List[str], "处理结果"]:
        """处理数据项"""
        if mode == "upper":
            return [item.upper() for item in items]
        return items
    
    @action(category="query")
    def get_summary(
        self,
        data: Annotated[List[dict], "数据列表"]
    ) -> Annotated[dict, "统计摘要"]:
        """获取数据摘要"""
        return {
            "count": len(data),
            "keys": list(data[0].keys()) if data else []
        }
```
