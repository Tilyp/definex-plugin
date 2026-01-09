import hashlib
import os
import shutil
from pathlib import Path

class CommonUtils:

    @staticmethod
    def get_file_hash(file_path: Path) -> str:
        """计算文件的 MD5 值（用于依赖缓存校验）"""
        if not file_path.exists():
            return ""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def cleanup_dir(path: Path):
        """递归清理构建目录中的冗余文件"""
        # 定义需要忽略的模式
        ignore_patterns = ["__pycache__", ".git", ".pytest_cache", ".deps_hash", ".venv", "_env"]

        for root, dirs, files in os.walk(path, topdown=False):
            for name in dirs:
                if any(p in name for p in ignore_patterns):
                    shutil.rmtree(Path(root) / name, ignore_errors=True)
            for name in files:
                if any(name.endswith(ext) for ext in [".pyc", ".pyo", ".pyd", ".log"]):
                    os.remove(Path(root) / name)

    @staticmethod
    def ensure_dir(path: Path):
        """确保目录存在"""
        path.mkdir(parents=True, exist_ok=True)