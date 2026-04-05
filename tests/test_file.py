import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import pytest
from src.files.file_manager import FileManager
from src.config.config import config_manager


class TestFileManager:
    """文件管理模块测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.file_manager = FileManager()
        self.config = config_manager.get_config()

    def test_move_to_finished(self):
        """测试移动文件到finished文件夹"""
        # 创建测试目录和文件
        test_dir = os.path.join(self.config.paths.working_dir, "test_file_mgmt")
        os.makedirs(test_dir, exist_ok=True)

        test_files = ["test1.txt", "test2.txt"]
        for f in test_files:
            with open(os.path.join(test_dir, f), "w") as fp:
                fp.write(f"Test content for {f}")

        success = self.file_manager.move_to_finished(test_dir)
        assert success is True

        # 验证文件已经被移动
        finished_files = self.file_manager.get_file_list(self.config.paths.finished_dir)
        assert len(finished_files) >= 2

    def test_archive_files(self):
        """测试归档文件"""
        # 先确保finished目录中有文件
        os.makedirs(self.config.paths.finished_dir, exist_ok=True)
        test_file = os.path.join(self.config.paths.finished_dir, "archive_test.txt")
        with open(test_file, "w") as f:
            f.write("test archive content")

        success = self.file_manager.archive_files()
        assert success is True

    def test_cleanup_expired_files(self):
        """测试清理过期文件"""
        success = self.file_manager.cleanup_expired_files()
        assert success is True

    def test_get_file_list(self):
        """测试获取文件列表"""
        files = self.file_manager.get_file_list(self.config.paths.working_dir)
        assert isinstance(files, list)

    def test_get_file_list_nonexistent(self):
        """测试获取不存在目录的文件列表"""
        files = self.file_manager.get_file_list("/nonexistent/path")
        assert files == []

    def test_get_directory_size(self):
        """测试获取目录大小"""
        size = self.file_manager.get_directory_size(self.config.paths.working_dir)
        assert isinstance(size, int)
        assert size >= 0

    def test_get_directory_size_nonexistent(self):
        """测试获取不存在目录的大小"""
        size = self.file_manager.get_directory_size("/nonexistent/path")
        assert size == 0
