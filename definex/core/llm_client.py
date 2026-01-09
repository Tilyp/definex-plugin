"""
LLM客户端管理器，支持多个AI模型
基于统一的LLMClientBase类
"""

from .llm_client_base import LLMClientBase


class LLMClientManager(LLMClientBase):
    """LLM客户端管理器 - 兼容现有接口"""
    
    def __init__(self):
        """初始化LLM客户端管理器"""
        super().__init__()
