from typing import Any, List, Dict, Optional, Type


class UIBase:
    """UI 属性基类，负责自动序列化"""
    def to_dict(self) -> Dict[str, Any]:
        data = {
            "widget": self.__class__.__name__.lower(),
            **{k: v for k, v in self.__dict__.items() if v is not None and not k.startswith("_")}
        }
        # 处理特殊映射，如 Select 的 options
        return data

class UI:
    # --- 1. 基础输入类 ---
    class Secret(UIBase):
        """密码输入框 (脱敏)"""
        pass

    class Textarea(UIBase):
        """长文本框"""
        def __init__(self, rows: int = 4, placeholder: str = ""):
            self.rows = rows
            self.placeholder = placeholder

    class CodeEditor(UIBase):
        """代码编辑器 (支持语法高亮)"""
        def __init__(self, language: str = "python", theme: str = "vs-dark"):
            self.language = language
            self.theme = theme

    # --- 2. 选择器类 ---
    class Select(UIBase):
        """单选下拉框"""
        def __init__(self, options: List[Dict[str, str]]):
            # options 格式: [{"label": "展示名", "value": "实际值"}]
            self.options = options

    class MultiSelect(UIBase):
        """多选下拉框"""
        def __init__(self, options: List[Dict[str, str]], max_count: Optional[int] = None):
            self.options = options
            self.max_count = max_count

    class Radio(UIBase):
        """单选按钮组"""
        def __init__(self, options: List[Dict[str, str]], direction: str = "horizontal"):
            self.options = options
            self.direction = direction

    # --- 3. 数值与范围选择 ---
    class Slider(UIBase):
        """滑动条"""
        def __init__(self, min: float, max: float, step: float = 1.0, unit: str = ""):
            self.min = min
            self.max = max
            self.step = step
            self.unit = unit

    class NumberRange(UIBase):
        """数值区间选择 (用于过滤)"""
        def __init__(self, min: float, max: float, precision: int = 2):
            self.min = min
            self.max = max
            self.precision = precision

    class DateTimePicker(UIBase):
        """日期时间选择器"""
        def __init__(self, type: str = "datetime", format: str = "YYYY-MM-DD HH:mm:ss"):
            self.type = type # date, datetime, month, range
            self.format = format

    # --- 4. 多模态与文件资源 (与 RustFS 联动) ---
    class ImagePicker(UIBase):
        """图片选择器"""
        def __init__(self, multiple: bool = False, accept: str = ".jpg,.png,.webp"):
            self.multiple = multiple
            self.accept = accept

    class VideoPicker(UIBase):
        """视频选择器"""
        def __init__(self, show_preview: bool = True):
            self.show_preview = show_preview

    class FilePicker(UIBase):
        """通用文件/Parquet选择器"""
        def __init__(self, accept: List[str] = [".parquet", ".csv"], allow_folder: bool = False):
            self.accept = accept
            self.allow_folder = allow_folder

    # --- 5. 布局与逻辑 ---
    class Group:
        """配置分组标签 (逻辑容器)"""
        def __init__(self, name: str, icon: str = "Setting", collapsible: bool = True):
            self.name = name
            self.icon = icon
            self.collapsible = collapsible

    class Condition(UIBase):
        """显隐控制条件 (当某字段满足某值时显示当前字段)"""
        def __init__(self, target_field: str, operator: str = "==", value: Any = None):
            self.target_field = target_field
            self.operator = operator # ==, !=, in, contains
            self.value = value

    class Column(UIBase):
        """表格列定义"""
        def __init__(self,
                     name: str,
                     title: str,
                     width: Optional[int] = None,
                     # 支持列内嵌套其他 UI 组件，如 Select, Switch
                     cell_widget: Optional[str] = None,
                     options: Optional[List[Dict[str, str]]] = None):
            self.name = name
            self.title = title
            self.width = width
            self.cell_widget = cell_widget
            self.options = options

    class Table(UIBase):
        """
        自动映射表格
        """
        def __init__(self,
                     row_class: Optional[Type] = None, # 可显式指定，也可由系统推导
                     data_source: str = "static",
                     can_add: bool = True,
                     can_delete: bool = True):
            self.row_class = row_class # 内部保存，用于反射
            self.data_source = data_source
            self.can_add = can_add
            self.can_delete = can_delete
            self.columns = [] # 最终生成的列定义


ICON_LIBRARY = {
    "1": {"icon": "🛠️", "label": "General Tool"},
    "2": {"icon": "🤖", "label": "AI & LLM"},
    "3": {"icon": "📁", "label": "File Management"},
    "4": {"icon": "🌐", "label": "Web Integration"},
    "5": {"icon": "🗄️", "label": "Database"},
    "6": {"icon": "🛡️", "label": "Security"},
}

class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'