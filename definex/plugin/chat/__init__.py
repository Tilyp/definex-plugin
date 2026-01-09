"""
DefineX AI聊天模块
提供智能的插件开发对话功能
"""
from .analyzer import ProjectAnalyzer
from .code_flow_manager import CodeFlowManager
from .code_guide import CodeGuide
from .commands import CommandHandler
from .conversation import ConversationManager, MessageRole
from .engine import AICodeEngine
from .todo_generator import TODOGenerator
from .writer import CodeWriter

__version__ = "0.1.0"
__all__ = [
    # 组件
    "ConversationManager",
    "MessageRole",
    "ProjectAnalyzer",
    "CodeWriter",
    "CommandHandler",
    "CodeGuide",
    "CodeFlowManager",
    "TODOGenerator",
    "AICodeEngine",
]
