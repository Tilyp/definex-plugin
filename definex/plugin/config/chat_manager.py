"""
聊天配置管理器
负责 AI 聊天相关的配置管理
"""
from typing import Optional

from .models import ChatConfig


class ChatManager:
    """聊天配置管理，专注于聊天功能的配置"""

    def __init__(self, storage):
        """
        Args:
            storage: 配置存储接口，提供 load/save 方法
        """
        self.storage = storage
        self._config_cache = None

    def _get_config(self) -> ChatConfig:
        """获取聊天配置（带缓存）"""
        if self._config_cache is None:
            raw_data = self.storage.load()
            chat_data = raw_data.get("chat", {})
            self._config_cache = ChatConfig.from_dict(chat_data)
        return self._config_cache

    def _save_config(self, config: ChatConfig) -> None:
        """保存聊天配置"""
        self._config_cache = config
        raw_data = self.storage.load()
        raw_data["chat"] = config.to_dict()
        self.storage.save(raw_data)

    def get_max_history_length(self) -> int:
        """获取最大历史记录长度"""
        config = self._get_config()
        return config.max_history_length

    def set_max_history_length(self, length: int) -> None:
        """设置最大历史记录长度"""
        config = self._get_config()
        config.max_history_length = max(1, length)
        self._save_config(config)

    def get_max_context_tokens(self) -> int:
        """获取最大上下文 token 数"""
        config = self._get_config()
        return config.max_context_tokens

    def set_max_context_tokens(self, tokens: int) -> None:
        """设置最大上下文 token 数"""
        config = self._get_config()
        config.max_context_tokens = max(100, tokens)
        self._save_config(config)

    def is_streaming_enabled(self) -> bool:
        """检查是否启用流式输出"""
        config = self._get_config()
        return config.enable_streaming

    def set_streaming(self, enabled: bool) -> None:
        """设置是否启用流式输出"""
        config = self._get_config()
        config.enable_streaming = enabled
        self._save_config(config)

    def is_auto_save_enabled(self) -> bool:
        """检查是否启用自动保存代码"""
        config = self._get_config()
        return config.auto_save_code

    def set_auto_save(self, enabled: bool) -> None:
        """设置是否启用自动保存代码"""
        config = self._get_config()
        config.auto_save_code = enabled
        self._save_config(config)

    def get_code_output_dir(self) -> str:
        """获取代码输出目录"""
        config = self._get_config()
        return config.code_output_dir

    def set_code_output_dir(self, directory: str) -> None:
        """设置代码输出目录"""
        config = self._get_config()
        config.code_output_dir = directory
        self._save_config(config)

    def get_default_filename(self) -> str:
        """获取默认文件名"""
        config = self._get_config()
        return config.default_filename

    def set_default_filename(self, filename: str) -> None:
        """设置默认文件名"""
        config = self._get_config()
        config.default_filename = filename
        self._save_config(config)

    def get_all_settings(self) -> ChatConfig:
        """获取所有聊天设置"""
        return self._get_config()

    def update_all_settings(
        self,
        max_history_length: Optional[int] = None,
        max_context_tokens: Optional[int] = None,
        enable_streaming: Optional[bool] = None,
        auto_save_code: Optional[bool] = None,
        code_output_dir: Optional[str] = None,
        default_filename: Optional[str] = None
    ) -> None:
        """批量更新聊天设置"""
        config = self._get_config()

        if max_history_length is not None:
            config.max_history_length = max(1, max_history_length)
        if max_context_tokens is not None:
            config.max_context_tokens = max(100, max_context_tokens)
        if enable_streaming is not None:
            config.enable_streaming = enable_streaming
        if auto_save_code is not None:
            config.auto_save_code = auto_save_code
        if code_output_dir is not None:
            config.code_output_dir = code_output_dir
        if default_filename is not None:
            config.default_filename = default_filename

        self._save_config(config)

    def reset_to_defaults(self) -> None:
        """重置为默认值"""
        default_config = ChatConfig()
        self._save_config(default_config)

    def clear_cache(self) -> None:
        """清除配置缓存，强制重新加载"""
        self._config_cache = None
