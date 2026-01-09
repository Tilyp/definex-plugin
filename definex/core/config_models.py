"""
LLM配置数据模型定义
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List


class ModelProvider(str, Enum):
    """模型提供商枚举"""
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    AZURE = "azure"
    QWEN = "qwen"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass
class LLMModelConfig:
    """单个LLM模型配置"""
    name: str  # 模型名称，如 "gpt-4", "claude-3", "deepseek-coder"
    provider: ModelProvider = ModelProvider.DEEPSEEK
    api_key: str = ""
    base_url: str = ""
    api_version: str = ""  # Azure等需要版本号
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 60  # 请求超时时间（秒）
    enabled: bool = True
    description: str = ""

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'LLMModelConfig':
        """从字典创建配置"""
        provider = data.get("provider", "deepseek")
        try:
            provider_enum = ModelProvider(provider.lower())
        except ValueError:
            provider_enum = ModelProvider.CUSTOM

        return cls(
            name=name,
            provider=provider_enum,
            api_key=data.get("api_key", ""),
            base_url=data.get("base_url", ""),
            api_version=data.get("api_version", ""),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 2000),
            timeout=data.get("timeout", 60),
            enabled=data.get("enabled", True),
            description=data.get("description", "")
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "provider": self.provider.value,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "api_version": self.api_version,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "enabled": self.enabled,
            "description": self.description
        }

    def validate(self) -> List[str]:
        """验证配置，返回错误信息列表"""
        errors = []

        if not self.name:
            errors.append("模型名称不能为空")

        if not self.api_key:
            errors.append(f"模型 {self.name} 的 API Key 未配置")

        if self.temperature < 0 or self.temperature > 2:
            errors.append(f"模型 {self.name} 的 temperature 必须在 0-2 之间")

        if self.max_tokens < 1 or self.max_tokens > 32000:
            errors.append(f"模型 {self.name} 的 max_tokens 必须在 1-32000 之间")

        if self.timeout < 1:
            errors.append(f"模型 {self.name} 的 timeout 必须大于 0")

        return errors


@dataclass
class LLMConfig:
    """LLM整体配置"""
    current_model: str = ""  # 当前选中的模型名称
    models: Dict[str, LLMModelConfig] = field(default_factory=dict)
    default_temperature: float = 0.7
    default_max_tokens: int = 2000

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMConfig':
        """从字典创建配置"""
        models_dict = data.get("models", {})
        models = {}
        for model_name, model_data in models_dict.items():
            models[model_name] = LLMModelConfig.from_dict(model_name, model_data)

        return cls(
            current_model=data.get("current_model", ""),
            models=models,
            default_temperature=data.get("default_temperature", 0.7),
            default_max_tokens=data.get("default_max_tokens", 2000)
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        models_dict = {}
        for model_name, model_config in self.models.items():
            models_dict[model_name] = model_config.to_dict()

        return {
            "current_model": self.current_model,
            "models": models_dict,
            "default_temperature": self.default_temperature,
            "default_max_tokens": self.default_max_tokens
        }

    def get_current_config(self) -> Optional[LLMModelConfig]:
        """获取当前模型的配置"""
        if self.current_model and self.current_model in self.models:
            return self.models[self.current_model]

        # 如果当前模型未设置，尝试使用第一个可用模型
        if self.models:
            first_model = next(iter(self.models.values()))
            self.current_model = first_model.name
            return first_model

        return None

    def get_all_config(self) -> Dict[str, Any]:
        """所有模型的配置"""
        # 如果当前模型未设置，尝试使用第一个可用模型
        models_dict = {}
        if self.models:
            for model_name, model_config in self.models.items():
                models_dict[model_name] = model_config.to_dict()
        return models_dict


    def add_model(self, model_config: LLMModelConfig):
        """添加或更新模型配置"""
        self.models[model_config.name] = model_config
        if not self.current_model:
            self.current_model = model_config.name

    def remove_model(self, model_name: str) -> bool:
        """移除模型配置"""
        if model_name in self.models:
            del self.models[model_name]
            # 如果移除的是当前模型，重置当前模型
            if self.current_model == model_name:
                self.current_model = next(iter(self.models), "") if self.models else ""
            return True
        return False

    def validate_all(self) -> Dict[str, List[str]]:
        """验证所有模型配置，返回错误字典"""
        errors = {}
        for model_name, model_config in self.models.items():
            model_errors = model_config.validate()
            if model_errors:
                errors[model_name] = model_errors
        return errors
