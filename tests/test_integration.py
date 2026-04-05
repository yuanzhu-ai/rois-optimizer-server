import sys
import os
import tempfile
import shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.api.integration import interface_integration


class TestInterfaceIntegration:
    """接口集成模块测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """每个测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_get_input_file_no_server(self):
        """测试获取input.gz文件（无服务器连接时应该失败）"""
        input_path = os.path.join(self.temp_dir, "input.gz")
        success = interface_integration.get_input_file(
            "test_task_123", input_path,
            url="http://localhost:99999/nonexistent",
            token="test_token"
        )
        assert success is False

    def test_send_output_file_no_server(self):
        """测试回传output.gz文件（无服务器连接时应该失败）"""
        output_path = os.path.join(self.temp_dir, "output.gz")
        with open(output_path, "w") as f:
            f.write("test output")

        success = interface_integration.send_output_file(
            "test_task_123", output_path,
            url="http://localhost:99999/nonexistent",
            token="test_token"
        )
        assert success is False

    def test_call_external_api_no_server(self):
        """测试调用外部API（无服务器连接时应该返回None）"""
        result = interface_integration.call_external_api(
            url="http://localhost:99999/nonexistent",
            token="test_token",
            method="GET"
        )
        assert result is None

    def test_call_external_api_invalid_method(self):
        """测试调用不支持的HTTP方法"""
        result = interface_integration.call_external_api(
            url="http://localhost:99999/nonexistent",
            token="test_token",
            method="DELETE"
        )
        assert result is None
