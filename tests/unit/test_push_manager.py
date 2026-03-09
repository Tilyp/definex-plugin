"""
Push 管理器测试
"""
import pytest
from pathlib import Path
import tempfile


class TestPushManager:
    """Push 管理器测试类"""

    @pytest.fixture
    def push_manager(self):
        """创建 PushManager 实例"""
        from definex.plugin.config.push_manager import PushManager
        from definex.plugin.storage.storage import FileStorage
        from definex.plugin.config.encryption import ConfigEncryption
        
        # 创建临时配置目录
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            config_file = config_dir / "config.yaml"
            key_file = config_dir / ".key"
            
            # 初始化存储
            encryption = ConfigEncryption(key_file)
            storage = FileStorage(config_file, encryption)
            
            # 创建 PushManager
            mgr = PushManager(storage)
            yield mgr

    def test_init(self, push_manager):
        """测试初始化"""
        assert push_manager is not None
        assert hasattr(push_manager, 'storage')
        assert hasattr(push_manager, '_config_cache')

    def test_add_or_update_environment(self, push_manager):
        """测试添加/更新环境"""
        push_manager.add_or_update_environment(
            env_name="dev",
            url="https://dev.example.com",
            token="dev_token_123",
            description="开发环境",
            timeout=30,
            enabled=True,
            set_as_default=True
        )
        
        config = push_manager._get_config()
        assert "dev" in config.environments
        assert config.environments["dev"].url == "https://dev.example.com"
        assert config.default_environment == "dev"

    def test_remove_environment(self, push_manager):
        """测试移除环境"""
        # 先添加环境
        push_manager.add_or_update_environment(
            env_name="temp",
            url="https://temp.example.com",
            token="temp_token"
        )
        
        # 移除环境
        result = push_manager.remove_environment("temp")
        assert result is True
        
        # 验证已移除
        config = push_manager._get_config()
        assert "temp" not in config.environments

    def test_list_environments(self, push_manager):
        """测试列出所有环境"""
        # 添加多个环境
        push_manager.add_or_update_environment("dev", "http://dev.com", "token1")
        push_manager.add_or_update_environment("prod", "http://prod.com", "token2")
        push_manager.add_or_update_environment("staging", "http://staging.com", "token3")
        
        envs = push_manager.list_environments()
        assert len(envs) == 3
        assert "dev" in envs
        assert "prod" in envs
        assert "staging" in envs

    def test_set_default_environment(self, push_manager):
        """测试设置默认环境"""
        # 添加两个环境
        push_manager.add_or_update_environment("dev", "http://dev.com", "token1")
        push_manager.add_or_update_environment("prod", "http://prod.com", "token2")
        
        # 设置 prod 为默认
        push_manager.set_default_environment("prod")
        
        config = push_manager._get_config()
        assert config.default_environment == "prod"

    def test_get_current_environment(self, push_manager):
        """测试获取当前环境"""
        # 添加并设置默认环境
        push_manager.add_or_update_environment(
            env_name="test",
            url="https://test.example.com",
            token="test_token",
            set_as_default=True
        )
        
        current = push_manager.get_current_environment()
        assert current is not None
        assert current.name == "test"
        assert current.url == "https://test.example.com"

    def test_enable_disable_environment(self, push_manager):
        """测试启用/禁用环境"""
        # 添加环境
        push_manager.add_or_update_environment(
            env_name="disabled_env",
            url="http://disabled.com",
            token="token",
            enabled=False
        )
        
        # 验证初始状态
        config = push_manager._get_config()
        assert config.environments["disabled_env"].enabled is False
        
        # 启用环境
        push_manager.enable_environment("disabled_env")
        config = push_manager._get_config()
        assert config.environments["disabled_env"].enabled is True
        
        # 禁用环境
        push_manager.disable_environment("disabled_env")
        config = push_manager._get_config()
        assert config.environments["disabled_env"].enabled is False

    def test_validate_environment(self, push_manager):
        """测试验证环境配置"""
        # 添加有效环境
        push_manager.add_or_update_environment(
            env_name="valid",
            url="https://valid.example.com",
            token="valid_token_123"
        )
        
        errors = push_manager.validate_all()
        assert len(errors) == 0 or "valid" not in errors
