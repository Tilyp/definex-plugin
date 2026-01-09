"""
LLM 模型配置管理器
负责 LLM 模型的增删改查和验证
"""
from typing import Dict, List, Optional

from definex.core import LLMConfig, LLMModelConfig
from definex.exception.exceptions import ModelNotFoundException


class LLMManager:
    """LLM 配置管理，专注于模型生命周期管理"""

    def __init__(self, storage):
        """
        Args:
            storage: 配置存储接口，提供 load/save 方法
        """
        self.storage = storage
        self._config_cache = None

    def _get_config(self) -> LLMConfig:
        """获取 LLM 配置（带缓存）"""
        if self._config_cache is None:
            raw_data = self.storage.load()
            llm_data = raw_data.get("llm", {})
            self._config_cache = LLMConfig.from_dict(llm_data)
        return self._config_cache

    def _save_config(self, config: LLMConfig) -> None:
        """保存 LLM 配置"""
        self._config_cache = config
        raw_data = self.storage.load()
        raw_data["llm"] = config.to_dict()
        self.storage.save(raw_data)

    def add_or_update_model(self, model_config: LLMModelConfig, set_as_current: bool = False) -> None:
        """
        添加或更新 LLM 模型

        Args:
            model_config: 模型配置
            set_as_current: 是否设为当前使用的模型
        """
        config = self._get_config()
        config.add_model(model_config)

        if set_as_current:
            config.current_model = model_config.name

        self._save_config(config)

    def remove_model(self, model_name: str) -> bool:
        """
        移除模型

        Args:
            model_name: 要移除的模型名称

        Returns:
            移除是否成功
        """
        config = self._get_config()
        if model_name not in config.models:
            return False

        config.remove_model(model_name)
        self._save_config(config)
        return True

    def set_current_model(self, model_name: str) -> None:
        """
        设置当前使用的模型

        Args:
            model_name: 模型名称

        Raises:
            ModelNotFoundException: 模型不存在时抛出
        """
        config = self._get_config()
        if model_name not in config.models:
            raise ModelNotFoundException(f"模型 '{model_name}' 不存在")

        config.current_model = model_name
        self._save_config(config)

    def get_current_model(self) -> Optional[LLMModelConfig]:
        """获取当前使用的模型配置"""
        config = self._get_config()
        return config.get_current_config()

    def get_current_model_name(self) -> Optional[str]:
        """获取当前使用的模型名称"""
        config = self._get_config()
        return config.current_model if config.current_model else None

    def get_model(self, model_name: str) -> Optional[LLMModelConfig]:
        """获取指定模型的配置"""
        config = self._get_config()
        return config.models.get(model_name)

    def list_model_names(self) -> List[str]:
        """列出所有模型名称"""
        config = self._get_config()
        return list(config.models.keys())

    def list_models(self) -> LLMConfig:
        """列出所有模型名称"""
        return self._get_config()

    def list_enabled_models(self) -> List[str]:
        """列出所有启用的模型名称"""
        config = self._get_config()
        return [
            name for name, model in config.models.items()
            if model.enabled
        ]

    def enable_model(self, model_name: str) -> None:
        """启用模型"""
        config = self._get_config()
        if model_name not in config.models:
            raise ModelNotFoundException(f"模型 '{model_name}' 不存在")

        config.models[model_name].enabled = True
        self._save_config(config)

    def disable_model(self, model_name: str) -> None:
        """禁用模型"""
        config = self._get_config()
        if model_name not in config.models:
            raise ModelNotFoundException(f"模型 '{model_name}' 不存在")

        config.models[model_name].enabled = False
        self._save_config(config)

    def validate_all(self) -> Dict[str, List[str]]:
        """验证所有模型配置，返回错误信息"""
        config = self._get_config()
        return config.validate_all()

    def model_exists(self, model_name: str) -> bool:
        """检查模型是否存在"""
        config = self._get_config()
        return model_name in config.models

    def get_default_temperature(self) -> float:
        """获取默认温度值"""
        config = self._get_config()
        return config.default_temperature

    def get_default_max_tokens(self) -> int:
        """获取默认最大 token 值"""
        config = self._get_config()
        return config.default_max_tokens

    def clear_cache(self) -> None:
        """清除配置缓存，强制重新加载"""
        self._config_cache = None
