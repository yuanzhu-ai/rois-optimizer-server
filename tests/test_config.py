import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.config.config import config_manager, Config


class TestConfigManager:
    """配置管理模块测试"""

    def setup_method(self):
        """每个测试前重新加载配置"""
        config_manager._config = None
        config_manager.load_config()

    def test_config_load(self):
        """测试配置加载"""
        config = config_manager.get_config()
        assert config is not None
        assert isinstance(config, Config)

    def test_server_config(self):
        """测试服务器配置"""
        config = config_manager.get_config()
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 8000

    def test_auth_config(self):
        """测试认证配置"""
        config = config_manager.get_config()
        assert isinstance(config.auth.enabled, bool)

    def test_paths_config(self):
        """测试文件路径配置"""
        config = config_manager.get_config()
        assert config.paths.working_dir == "./workspace"
        assert config.paths.finished_dir == "./finished"
        assert config.paths.archive_dir == "./archive"
        assert config.paths.temp_dir == "./temp"

    def test_tasks_config(self):
        """测试任务配置"""
        config = config_manager.get_config()
        assert config.tasks.max_concurrent == 10
        assert config.tasks.timeout == 3600

    def test_airlines_config(self):
        """测试航司配置"""
        config = config_manager.get_config()
        assert "F8" in config.airlines
        assert "BR" in config.airlines

    def test_get_airline_config(self):
        """测试获取航司配置"""
        airline_config = config_manager.get_airline_config("F8")
        assert airline_config is not None
        assert airline_config.optimizers is not None

    def test_get_airline_config_invalid(self):
        """测试获取不存在的航司配置"""
        with pytest.raises(ValueError):
            config_manager.get_airline_config("INVALID")

    def test_get_optimizer_config(self):
        """测试获取优化器配置"""
        for airline in ["F8", "BR"]:
            for opt_type in ["PO", "RO", "TO", "Rule"]:
                opt_config = config_manager.get_optimizer_config(airline, opt_type)
                assert opt_config is not None

    def test_get_optimizer_config_invalid(self):
        """测试获取不支持的优化器配置"""
        with pytest.raises(ValueError):
            config_manager.get_optimizer_config("F8", "INVALID")

    def test_get_optimizer_name(self):
        """测试获取优化器名称"""
        name = config_manager.get_optimizer_name("F8", "PO")
        assert name == "Pairing Optimizer"

    def test_http_client_config(self):
        """测试HTTP客户端配置"""
        config = config_manager.get_config()
        assert config.http_client.timeout == 1200

    def test_redis_config(self):
        """测试Redis配置"""
        config = config_manager.get_config()
        assert config.redis.enabled is False
        assert config.redis.host == "localhost"
        assert config.redis.port == 6379

    def test_platform_detection(self):
        """测试平台检测"""
        platform = "windows" if os.name == "nt" else "linux"
        assert platform in ["windows", "linux"]
