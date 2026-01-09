"""
配置加密处理模块
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any

from cryptography.exceptions import InvalidSignature
from cryptography.fernet import Fernet, InvalidToken

from definex.exception.exceptions import ConfigEncryptionException


class ConfigEncryption:
    """配置加密处理器"""

    SECRET_FIELDS = {"api_key", "token", "secret_key", "password"}

    def __init__(self, key_file: Path):
        self.key_file = key_file
        self._cipher = self._init_cipher()

    def _init_cipher(self) -> Fernet:
        """初始化加密器"""
        # 确保密钥文件所在目录存在
        self.key_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.key_file.exists():
            try:
                key = Fernet.generate_key()
                self.key_file.write_bytes(key)
                # 设置权限，仅当前用户可读写 (Linux/macOS)
                if sys.platform != "win32":
                    os.chmod(self.key_file, 0o600)
            except Exception as e:
                raise ConfigEncryptionException(f"生成密钥失败: {e}")
        else:
            try:
                key = self.key_file.read_bytes()
            except Exception as e:
                raise ConfigEncryptionException(f"读取密钥失败: {e}")

        try:
            return Fernet(key)
        except Exception as e:
            raise ConfigEncryptionException(f"初始化加密器失败: {e}")

    def encrypt_value(self, value: str) -> str:
        """加密单个值"""
        if not value:
            return value

        try:
            encrypted = self._cipher.encrypt(value.encode())
            return encrypted.decode()
        except Exception as e:
            raise ConfigEncryptionException(f"加密失败: {e}")

    def decrypt_value(self, value: str) -> str:
        """解密单个值"""
        if not value:
            return value

        # 检查是否是加密过的字符串（Fernet加密后的字符串以特定前缀开头）
        if not value.startswith("gAAAAA"):
            return value

        try:
            decrypted = self._cipher.decrypt(value.encode())
            return decrypted.decode()
        except (InvalidToken, InvalidSignature) as e:
            raise ConfigEncryptionException(f"解密失败：无效的密钥或数据 {e}")
        except Exception as e:
            raise ConfigEncryptionException(f"解密失败: {e}")

    def process_secrets(self, data: Dict[str, Any], encrypt: bool = True) -> Dict[str, Any]:
        """递归处理字典中的敏感字段"""
        if not isinstance(data, dict):
            return data

        result = data.copy()

        for key, value in result.items():
            if key in self.SECRET_FIELDS and isinstance(value, str) and value:
                try:
                    if encrypt:
                        # 避免重复加密
                        if not value.startswith("gAAAAA"):
                            result[key] = self.encrypt_value(value)
                    else:
                        # 尝试解密（如果是加密的）
                        if value.startswith("gAAAAA"):
                            result[key] = self.decrypt_value(value)
                except ConfigEncryptionException as e:
                    # 解密失败时，如果我们是解密操作，就保留原值
                    if not encrypt:
                        # 可能是旧的加密格式或其他问题，保留原值
                        pass
                    else:
                        raise

            elif isinstance(value, dict):
                result[key] = self.process_secrets(value, encrypt)
            elif isinstance(value, list):
                # 处理列表中的字典
                new_list = []
                for item in value:
                    if isinstance(item, dict):
                        new_list.append(self.process_secrets(item, encrypt))
                    else:
                        new_list.append(item)
                result[key] = new_list

        return result

    def rotate_key(self, new_key_file: Path = None) -> bool:
        """轮换加密密钥"""
        try:
            # 备份旧密钥
            old_key_file = self.key_file.with_suffix(f".key.bak.{int(os.path.getctime(str(self.key_file)))}")
            if self.key_file.exists():
                import shutil
                shutil.copy2(self.key_file, old_key_file)

            # 生成新密钥
            new_key = Fernet.generate_key()

            # 如果指定了新密钥文件，使用它
            if new_key_file:
                new_key_file.write_bytes(new_key)
                if sys.platform != "win32":
                    os.chmod(new_key_file, 0o600)
                self.key_file = new_key_file
            else:
                # 覆盖原密钥文件
                self.key_file.write_bytes(new_key)
                if sys.platform != "win32":
                    os.chmod(self.key_file, 0o600)

            # 重新初始化加密器
            self._cipher = Fernet(new_key)

            return True

        except Exception as e:
            raise ConfigEncryptionException(f"轮换密钥失败: {e}")

    def get_key_info(self) -> Dict[str, Any]:
        """获取密钥信息"""
        try:
            if self.key_file.exists():
                key_data = self.key_file.read_bytes()
                key_size = len(key_data)
                created_time = os.path.getctime(str(self.key_file))

                return {
                    "path": str(self.key_file),
                    "size": key_size,
                    "created": created_time,
                    "exists": True
                }
            else:
                return {
                    "path": str(self.key_file),
                    "exists": False
                }
        except Exception as e:
            raise ConfigEncryptionException(f"获取密钥信息失败: {e}")