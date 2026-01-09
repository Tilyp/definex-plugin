"""
配置管理器 - 主入口
聚合 LLM、Push、Chat 三个子管理器
"""
from pathlib import Path
from typing import Dict, Any, Optional

from rich.console import Console

from definex.core import LLMConfig
from definex.core import LLMModelConfig, ModelProvider
from definex.exception.exceptions import ConfigException
from definex.plugin.storage.storage import FileStorage
from .chat_manager import ChatManager
from .encryption import ConfigEncryption
from .llm_manager import LLMManager
from .models import PushEnvironment, ChatConfig
from .push_manager import PushManager


class ConfigManager:
    """
    统一的配置管理器

    责任：
    1. 初始化存储和各子管理器
    2. 提供高层配置接口
    3. 支持配置导入导出
    4. 提供脱敏的配置显示
    """

    def __init__(self, console: Console, config_dir: Optional[Path] = None):
        self.console = console
        self.config_dir = config_dir or Path.home() / ".definex"
        self.config_file = self.config_dir / "config.yaml"

        # 创建配置目录
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 初始化加密处理器
        self.encryption = ConfigEncryption(self.config_dir / ".key")

        # 初始化存储
        self.storage = FileStorage(self.config_file, self.encryption)

        # 初始化子管理器
        self.llm = LLMManager(self.storage)
        self.push = PushManager(self.storage)
        self.chat = ChatManager(self.storage)

    # ===== LLM 配置兼容性方法 =====

    def get_llm_config(self):
        """获取 LLM 配置（兼容旧接口）"""
        from definex.core import LLMConfig
        raw_data = self.storage.load()
        return LLMConfig.from_dict(raw_data.get("llm", {}))

    def save_llm_config(self, llm_config):
        """保存 LLM 配置（兼容旧接口）"""
        raw_data = self.storage.load()
        raw_data["llm"] = llm_config.to_dict()
        self.storage.save(raw_data)

    def get_current_llm_config(self) -> Optional[Dict[str, Any]]:
        """获取当前 LLM 模型的配置"""
        current = self.llm.get_current_model()
        if current:
            config_dict = current.to_dict()
            config_dict["model"] = current.name
            config_dict["provider"] = current.provider.value
            return config_dict
        return None

    def add_or_update_llm_model(self, model_config: LLMModelConfig, set_as_current: bool = False):
        """添加或更新 LLM 模型"""
        self.llm.add_or_update_model(model_config, set_as_current)

    def set_current_llm_model(self, model_name: str):
        """设置当前 LLM 模型"""
        self.llm.set_current_model(model_name)

    def remove_llm_model(self, model_name: str) -> bool:
        """移除 LLM 模型"""
        return self.llm.remove_model(model_name)

    def get_llm_model_names(self) -> list:
        """获取所有 LLM 模型名称"""
        return self.llm.list_model_names()

    def get_llm_model(self) -> LLMConfig:
        """获取所有 LLM 模型信息"""
        return self.llm.list_models()

    def get_enabled_llm_models(self) -> list:
        """获取所有启用的 LLM 模型"""
        return self.llm.list_enabled_models()

    def validate_llm_config(self) -> Dict[str, list]:
        """验证 LLM 配置"""
        return self.llm.validate_all()

    # ===== Push 配置兼容性方法 =====

    def get_push_config(self):
        """获取发布配置（兼容旧接口）"""
        from .models import PushConfig
        raw_data = self.storage.load()
        return PushConfig.from_dict(raw_data.get("push", {}))

    def save_push_config(self, push_config):
        """保存发布配置（兼容旧接口）"""
        raw_data = self.storage.load()
        raw_data["push"] = push_config.to_dict()
        self.storage.save(raw_data)

    def set_env_config(self, env_name: str, url: str = "", token: str = "",
                       description: str = "", timeout: int = 30, enabled: bool = True):
        """设置发布环境配置"""
        self.push.add_or_update_environment(
            env_name, url, token, description, timeout, enabled,
            set_as_default=not self.push.list_environments()  # 第一个环境设为默认
        )

    def remove_environment(self, env_name: str) -> bool:
        """移除发布环境"""
        return self.push.remove_environment(env_name)

    def get_environment_names(self) -> list:
        """获取所有发布环境名称"""
        return self.push.list_environments()

    # ===== Chat 配置兼容性方法 =====

    def get_chat_config(self) -> ChatConfig:
        """获取聊天配置"""
        return self.chat.get_all_settings()

    def save_chat_config(self, chat_config: ChatConfig):
        """保存聊天配置"""
        raw_data = self.storage.load()
        raw_data["chat"] = chat_config.to_dict()
        self.storage.save(raw_data)

    # ===== 通用配置方法 =====

    def get_section(self, section: str) -> Dict[str, Any]:
        """获取配置分区"""
        if section == "llm":
            config = self.get_current_llm_config()
            return config or {}
        elif section == "push":
            push_config = self.get_push_config()
            result = {"default": push_config.default_environment, "environments": {}}
            for env_name, env_config in push_config.environments.items():
                result["environments"][env_name] = env_config.to_dict()
            return result
        elif section == "chat":
            chat_config = self.get_chat_config()
            return chat_config.to_dict()
        else:
            raw_data = self.storage.load()
            return raw_data.get(section, {})

    def set_section(self, section: str, data: Dict[str, Any]):
        """设置配置分区"""
        if section == "llm":
            model_name = data.get("model", "deepseek-chat")
            provider_str = data.get("provider", "deepseek")
            try:
                provider = ModelProvider(provider_str.lower())
            except ValueError:
                provider = ModelProvider.CUSTOM

            model_config = LLMModelConfig(
                name=model_name,
                provider=provider,
                api_key=data.get("api_key", ""),
                base_url=data.get("base_url", ""),
                api_version=data.get("api_version", ""),
                temperature=data.get("temperature", 0.7),
                max_tokens=data.get("max_tokens", 2000),
                timeout=data.get("timeout", 60),
                enabled=data.get("enabled", True),
                description=data.get("description", "")
            )
            self.add_or_update_llm_model(model_config, set_as_current=True)

        elif section == "push":
            push_config = self.get_push_config()
            env_name =  data.get("env", "default")
            push_config.default_environment = data.get("default", env_name)
            push_config.environments[env_name] = PushEnvironment(
                name=env_name,
                url=data.get("url", ""),
                token=data.get("token", ""),
                description=data.get("description", ""),
                timeout=data.get("timeout", 30),
                enabled=data.get("enabled", True)
            )
            self.save_push_config(push_config)

        elif section == "chat":
            chat_config = ChatConfig.from_dict(data)
            self.save_chat_config(chat_config)

        else:
            raw_data = self.storage.load()
            if section not in raw_data:
                raw_data[section] = {}
            update_data = {k: v for k, v in data.items() if v is not None}
            raw_data[section].update(update_data)
            self.storage.save(raw_data)

    # ===== 配置显示和导入导出 =====

    def get_masked_config(self) -> Dict[str, Any]:
        """获取脱敏后的配置（用于显示）"""
        return self.storage.export_config(None, include_secrets=False) if False else self._mask_config()

    def _mask_config(self) -> Dict[str, Any]:
        """脱敏配置"""
        raw_data = self.storage.load()
        secret_fields = {"api_key", "token", "secret_key", "password"}

        def mask_recursive(obj):
            if isinstance(obj, dict):
                return {
                    k: "[green]********[/green]" if k in secret_fields and v else mask_recursive(v)
                    for k, v in obj.items()
                }
            elif isinstance(obj, list):
                return [mask_recursive(item) for item in obj]
            else:
                return obj if obj else "[yellow]未设置[/yellow]"

        return mask_recursive(raw_data)

    def export_config(self, export_path: Path, include_secrets: bool = False) -> bool:
        """导出配置"""
        try:
            self.storage.export_config(export_path, include_secrets)
            return True
        except Exception as e:
            self.console.print(f"[red]❌ 导出配置失败: {e}[/red]")
            return False

    def import_config(self, import_path: Path, merge: bool = True) -> bool:
        """导入配置"""
        try:
            self.storage.import_config(import_path, merge)
            return True
        except Exception as e:
            self.console.print(f"[red]❌ 导入配置失败: {e}[/red]")
            return False

    def reset_config(self):
        """重置配置为默认值"""
        try:
            if self.config_file.exists():
                # 备份当前配置
                backup_file = self.config_file.with_suffix(f".yaml.bak.{int(self.config_file.stat().st_mtime)}")
                import shutil
                shutil.copy2(self.config_file, backup_file)

            # 删除配置文件
            if self.config_file.exists():
                self.config_file.unlink()

            # 重新初始化
            self.storage._ensure_config_file()
            self.storage.clear_cache()
            self.llm.clear_cache()
            self.push.clear_cache()
            self.chat.clear_cache()

            self.console.print("[bold green]✅ 配置已重置为默认值[/bold green]")
        except Exception as e:
            self.console.print(f"[red]❌ 重置配置失败: {e}[/red]")

    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息"""
        try:
            if self.config_file.exists():
                file_size = self.config_file.stat().st_size
                modified_time = self.config_file.stat().st_mtime
                from datetime import datetime
                return {
                    "config_path": str(self.config_file),
                    "config_size": file_size,
                    "last_modified": datetime.fromtimestamp(modified_time).isoformat(),
                    "key_info": self.encryption.get_key_info(),
                    "exists": True
                }
            else:
                return {"config_path": str(self.config_file), "exists": False}
        except Exception as e:
            raise ConfigException(f"获取配置信息失败: {e}")
