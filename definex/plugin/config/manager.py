"""
配置管理器 - 主入口
聚合 Push 子管理器
"""
from pathlib import Path
from typing import Dict, Any, Optional, List

from rich.console import Console

from definex.exception.exceptions import ConfigException
from definex.plugin.storage.storage import FileStorage
from .encryption import ConfigEncryption
from .models import PushEnvironment
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
        self.push = PushManager(self.storage)

    # ===== Push配置方法 =====

    def get_push_config(self) -> 'PushConfig':
        """获取发布配置（兼容旧接口）"""
        from .models import PushConfig
        raw_data = self.storage.load()
        return PushConfig.from_dict(raw_data.get("push", {}))

    def save_push_config(self, push_config: 'PushConfig') -> None:
        """保存发布配置（兼容旧接口）"""
        raw_data = self.storage.load()
        raw_data["push"] = push_config.to_dict()
        self.storage.save(raw_data)

    def add_environment(
        self,
        env_name: str,
        url: str = "",
        token: str = "",
        description: str = "",
        timeout: int = 30,
        enabled: bool = True,
        set_as_default: bool = False
    ) -> None:
        """添加发布环境配置"""
        self.push.add_or_update_environment(
            env_name, url, token, description, timeout, enabled,
            set_as_default=set_as_default
        )

    def update_environment(
        self,
        env_name: str,
        url: str = "",
        token: str = "",
        description: str = "",
        timeout: int = 30,
        enabled: bool = True
    ) -> None:
        """更新发布环境配置"""
        self.push.add_or_update_environment(
            env_name, url, token, description, timeout, enabled,
            set_as_default=False
        )

    def delete_environment(self, env_name: str) -> bool:
        """删除发布环境"""
        return self.push.remove_environment(env_name)

    def list_environments(self) -> List[str]:
        """获取所有发布环境名称"""
        return self.push.list_environments()

    # ===== 通用配置方法 =====

    def get_section(self, section: str) -> Dict[str, Any]:
        """获取配置分区"""
        if section == "push":
            push_config = self.get_push_config()
            result = {"default": push_config.default_environment, "environments": {}}
            for env_name, env_config in push_config.environments.items():
                result["environments"][env_name] = env_config.to_dict()
            return result
        else:
            raw_data = self.storage.load()
            return raw_data.get(section, {})

    def set_section(self, section: str, data: Dict[str, Any]):
        """设置配置分区"""
        if section == "push":
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
            self.push.clear_cache()

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
