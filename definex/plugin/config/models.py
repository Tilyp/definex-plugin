"""
配置数据模型定义（Push和Chat相关）
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class PushEnvironment:
    """推送环境配置"""
    name: str
    url: str = ""
    token: str = ""
    description: str = ""
    timeout: int = 30
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "url": self.url,
            "token": self.token,
            "description": self.description,
            "timeout": self.timeout,
            "enabled": self.enabled
        }


@dataclass
class PushConfig:
    """推送配置"""
    default_environment: str = ""
    environments: Dict[str, PushEnvironment] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PushConfig':
        """从字典创建配置"""
        envs_dict = data.get("environments", {})
        environments = {}
        for env_name, env_data in envs_dict.items():
            environments[env_name] = PushEnvironment(
                name=env_name,
                url=env_data.get("url", ""),
                token=env_data.get("token", ""),
                description=env_data.get("description", ""),
                timeout=env_data.get("timeout", 30),
                enabled=env_data.get("enabled", True)
            )

        return cls(
            default_environment=data.get("default", ""),
            environments=environments
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        envs_dict = {}
        for env_name, env_config in self.environments.items():
            envs_dict[env_name] = env_config.to_dict()

        return {
            "default": self.default_environment,
            "environments": envs_dict
        }

    def get_current_environment(self) -> Optional[PushEnvironment]:
        """获取当前环境配置"""
        if self.default_environment and self.default_environment in self.environments:
            return self.environments[self.default_environment]
        return None


@dataclass
class ChatConfig:
    """聊天相关配置"""
    max_history_length: int = 10
    max_context_tokens: int = 4000
    enable_streaming: bool = True
    auto_save_code: bool = False
    code_output_dir: str = "tools"
    default_filename: str = "main.py"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatConfig':
        """从字典创建配置"""
        return cls(
            max_history_length=data.get("max_history_length", 10),
            max_context_tokens=data.get("max_context_tokens", 4000),
            enable_streaming=data.get("enable_streaming", True),
            auto_save_code=data.get("auto_save_code", False),
            code_output_dir=data.get("code_output_dir", "tools"),
            default_filename=data.get("default_filename", "main.py")
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "max_history_length": self.max_history_length,
            "max_context_tokens": self.max_context_tokens,
            "enable_streaming": self.enable_streaming,
            "auto_save_code": self.auto_save_code,
            "code_output_dir": self.code_output_dir,
            "default_filename": self.default_filename
        }
