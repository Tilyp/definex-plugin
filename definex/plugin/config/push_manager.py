"""
发布环境配置管理器
负责发布环境的增删改查
"""
from typing import List, Optional

from definex.exception.exceptions import ConfigException
from .models import PushConfig, PushEnvironment


class PushManager:
    """发布环境配置管理，专注于环境生命周期管理"""

    def __init__(self, storage):
        """
        Args:
            storage: 配置存储接口，提供 load/save 方法
        """
        self.storage = storage
        self._config_cache = None

    def _get_config(self) -> PushConfig:
        """获取发布配置（带缓存）"""
        if self._config_cache is None:
            raw_data = self.storage.load()
            push_data = raw_data.get("push", {})
            self._config_cache = PushConfig.from_dict(push_data)
        return self._config_cache

    def _save_config(self, config: PushConfig) -> None:
        """保存发布配置"""
        self._config_cache = config
        raw_data = self.storage.load()
        raw_data["push"] = config.to_dict()
        self.storage.save(raw_data)

    def add_or_update_environment(
        self,
        env_name: str,
        url: str,
        token: str,
        description: str = "",
        timeout: int = 30,
        enabled: bool = True,
        set_as_default: bool = False
    ) -> None:
        """
        添加或更新发布环境

        Args:
            env_name: 环境名称 (如 'dev', 'prod')
            url: 发布服务器地址
            token: 认证令牌
            description: 环境描述
            timeout: 请求超时时间（秒）
            enabled: 是否启用该环境
            set_as_default: 是否设为默认环境
        """
        if not url or not token:
            raise ConfigException("发布环境的 URL 和 Token 不能为空")

        config = self._get_config()
        environment = PushEnvironment(
            name=env_name,
            url=url,
            token=token,
            description=description,
            timeout=timeout,
            enabled=enabled
        )

        config.environments[env_name] = environment

        if set_as_default or not config.default_environment:
            config.default_environment = env_name

        self._save_config(config)

    def remove_environment(self, env_name: str) -> bool:
        """
        移除发布环境

        Args:
            env_name: 环境名称

        Returns:
            移除是否成功
        """
        config = self._get_config()
        if env_name not in config.environments:
            return False

        del config.environments[env_name]

        # 如果移除的是默认环境，重置
        if config.default_environment == env_name:
            config.default_environment = (
                next(iter(config.environments), "")
                if config.environments
                else ""
            )

        self._save_config(config)
        return True

    def set_default_environment(self, env_name: str) -> None:
        """
        设置默认发布环境

        Args:
            env_name: 环境名称

        Raises:
            ConfigException: 环境不存在时抛出
        """
        config = self._get_config()
        if env_name not in config.environments:
            raise ConfigException(f"发布环境 '{env_name}' 不存在")

        config.default_environment = env_name
        self._save_config(config)

    def get_default_environment(self) -> Optional[PushEnvironment]:
        """获取默认发布环境配置"""
        config = self._get_config()
        return config.get_current_environment()

    def get_environment(self, env_name: str) -> Optional[PushEnvironment]:
        """获取指定环境的配置"""
        config = self._get_config()
        return config.environments.get(env_name)

    def list_environments(self) -> List[str]:
        """列出所有环境名称"""
        config = self._get_config()
        return list(config.environments.keys())

    def list_enabled_environments(self) -> List[str]:
        """列出所有启用的环境名称"""
        config = self._get_config()
        return [
            name for name, env in config.environments.items()
            if env.enabled
        ]

    def enable_environment(self, env_name: str) -> None:
        """启用环境"""
        config = self._get_config()
        if env_name not in config.environments:
            raise ConfigException(f"发布环境 '{env_name}' 不存在")

        config.environments[env_name].enabled = True
        self._save_config(config)

    def disable_environment(self, env_name: str) -> None:
        """禁用环境"""
        config = self._get_config()
        if env_name not in config.environments:
            raise ConfigException(f"发布环境 '{env_name}' 不存在")

        config.environments[env_name].enabled = False
        self._save_config(config)

    def environment_exists(self, env_name: str) -> bool:
        """检查环境是否存在"""
        config = self._get_config()
        return env_name in config.environments

    def get_default_environment_name(self) -> Optional[str]:
        """获取默认环境名称"""
        config = self._get_config()
        return config.default_environment if config.default_environment else None

    def clear_cache(self) -> None:
        """清除配置缓存，强制重新加载"""
        self._config_cache = None
