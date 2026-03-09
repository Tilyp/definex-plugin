"""
配置管理器测试
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock


class TestConfigManager:
    """配置管理器测试类"""

    @pytest.fixture
    def config_manager(self):
        """创建配置管理器实例"""
        from definex.plugin.config.manager import ConfigManager
        from rich.console import Console
        
        console = Console()
        # 使用临时配置目录
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config_mgr = ConfigManager(console, config_dir=Path(tmpdir))
            yield config_mgr

    def test_init(self, config_manager):
        """测试初始化"""
        assert config_manager is not None
        assert hasattr(config_manager, 'push')
        assert hasattr(config_manager, 'storage')

    def test_get_push_config(self, config_manager):
        """测试获取发布配置"""
        from definex.plugin.config.models import PushConfig
        
        config = config_manager.get_push_config()
        assert isinstance(config, PushConfig)
        assert config.default_environment == ""

    def test_set_env_config(self, config_manager):
        """测试设置环境配置"""
        config_manager.set_env_config(
            env_name="test",
            url="https://test.example.com",
            token="test_token_123"
        )
        
        config = config_manager.get_push_config()
        assert "test" in config.environments
        assert config.environments["test"].url == "https://test.example.com"

    def test_remove_environment(self, config_manager):
        """测试移除环境"""
        # 先添加环境
        config_manager.set_env_config(
            env_name="temp",
            url="https://temp.example.com",
            token="temp_token"
        )
        
        # 再移除
        result = config_manager.remove_environment("temp")
        assert result is True
        
        # 验证已移除
        config = config_manager.get_push_config()
        assert "temp" not in config.environments

    def test_get_environment_names(self, config_manager):
        """测试获取环境名称列表"""
        # 添加多个环境
        config_manager.set_env_config("dev", "http://dev.com", "token1")
        config_manager.set_env_config("prod", "http://prod.com", "token2")
        
        names = config_manager.get_environment_names()
        assert len(names) == 2
        assert "dev" in names
        assert "prod" in names
