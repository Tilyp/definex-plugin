"""
交互式菜单引导模块

架构：
- views.py: UI 层（菜单、表格、表单渲染）
- handlers.py: 业务逻辑层（处理用户交互）
- guide.py: 协调层（主循环和流程控制）
"""

from .guide import InteractiveGuide

__all__ = ["InteractiveGuide"]
