"""
配置存储接口和实现
抽象配置的加载和保存逻辑
"""
import copy
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import yaml

from definex.exception.exceptions import ConfigException
from definex.plugin.config.encryption import ConfigEncryption


class StorageInterface(ABC):
    """配置存储的抽象接口"""

    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """加载配置"""
        pass

    @abstractmethod
    def save(self, data: Dict[str, Any]) -> None:
        """保存配置"""
        pass


class FileStorage(StorageInterface):
    """YAML 文件存储实现"""

    def __init__(self, config_file: Path, encryption: ConfigEncryption):
        """
        Args:
            config_file: 配置文件路径
            encryption: 加密处理器
        """
        self.config_file = config_file
        self.encryption = encryption
        self._cache = None
        self._ensure_config_file()

    def _ensure_config_file(self) -> None:
        """确保配置文件存在"""
        if not self.config_file.exists():
            default_config = {
                "version": "1.0.0",
                "last_updated": datetime.now().isoformat(),
                "llm": {
                    "current_model": "",
                    "models": {},
                    "default_temperature": 0.7,
                    "default_max_tokens": 2000
                },
                "push": {
                    "default": "",
                    "environments": {}
                },
                "chat": {
                    "max_history_length": 10,
                    "max_context_tokens": 4000,
                    "enable_streaming": True,
                    "auto_save_code": False,
                    "code_output_dir": "tools",
                    "default_filename": "main.py"
                }
            }
            self.save(default_config)

    def load(self) -> Dict[str, Any]:
        """加载配置，使用缓存避免重复 I/O"""
        if self._cache is not None:
            return self._cache

        if not self.config_file.exists():
            self._ensure_config_file()

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            # 解密敏感字段
            config = self.encryption.process_secrets(config, encrypt=False)
            self._cache = config
            return config
        except Exception as e:
            raise ConfigException(f"加载配置文件失败: {e}")

    def save(self, data: Dict[str, Any]) -> None:
        """保存配置"""
        try:
            # 深拷贝数据，避免修改原始数据
            to_save = copy.deepcopy(data)

            # 更新元数据
            to_save["version"] = to_save.get("version", "1.0.0")
            to_save["last_updated"] = datetime.now().isoformat()

            # 清理数据中的特殊字符
            to_save = self._sanitize_data(to_save)

            # 加密敏感字段
            to_save = self.encryption.process_secrets(to_save, encrypt=True)

            # 创建目录
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(to_save, f, allow_unicode=True, sort_keys=False, indent=2)

            # 清空缓存
            self._cache = None

        except Exception as e:
            raise ConfigException(f"保存配置文件失败: {e}")

    def _sanitize_data(self, data: Any) -> Any:
        """清理数据中的不可序列化内容"""
        if isinstance(data, dict):
            return {
                self._clean_string(k): self._sanitize_data(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        elif isinstance(data, str):
            return self._clean_string(data)
        else:
            return data

    def _clean_string(self, text: str) -> str:
        """清理字符串中的控制字符"""
        if not isinstance(text, str):
            return text

        # 移除控制字符
        cleaned = ''.join(
            char for char in text
            if char.isprintable() or char in '\n\r\t'
        )

        # 移除代理对字符
        cleaned = ''.join(
            char for char in cleaned
            if not ('\ud800' <= char <= '\udfff')
        )

        # 限制长度
        if len(cleaned) > 10000:
            cleaned = cleaned[:10000] + "...[已截断]"

        return cleaned

    def clear_cache(self) -> None:
        """清除缓存，强制重新加载"""
        self._cache = None

    def export_config(self, export_path: Path, include_secrets: bool = False) -> None:
        """导出配置"""
        config = self.load()

        if not include_secrets:
            # 脱敏敏感信息
            config = self._mask_secrets(config)

        try:
            export_path.parent.mkdir(parents=True, exist_ok=True)
            with open(export_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, indent=2)
        except Exception as e:
            raise ConfigException(f"导出配置失败: {e}")

    def import_config(self, import_path: Path, merge: bool = True) -> None:
        """导入配置"""
        if not import_path.exists():
            raise ConfigException(f"导入文件不存在: {import_path}")

        try:
            with open(import_path, "r", encoding="utf-8") as f:
                imported_config = yaml.safe_load(f) or {}

            if merge:
                current_config = self.load()
                self._deep_merge(current_config, imported_config)
                self.save(current_config)
            else:
                self.save(imported_config)
        except Exception as e:
            raise ConfigException(f"导入配置失败: {e}")

    def _mask_secrets(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """脱敏敏感字段"""
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
                return obj

        return mask_recursive(data)

    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """深度合并字典"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
