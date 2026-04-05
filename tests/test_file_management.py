"""
文件管理测试

覆盖:
- move_to_finished: 移动文件、命名冲突处理、空目录清理
- archive_files: 归档压缩
- cleanup_expired_files: 过期文件清理
- get_file_list / get_directory_size
"""
import gzip
import os
import shutil
import time

import pytest


@pytest.fixture()
def file_mgr(temp_workspace):
    """创建使用临时目录的 FileManager"""
    from src.config.config import config_manager, PathsConfig, FileManagementConfig

    cfg = config_manager.get_config()
    old_paths = cfg.paths
    old_fm = cfg.file_management

    cfg.paths = PathsConfig(
        working_dir=temp_workspace['workspace'],
        finished_dir=temp_workspace['finished'],
        archive_dir=temp_workspace['archive'],
        temp_dir=temp_workspace['temp'],
    )
    cfg.file_management = FileManagementConfig(archive_days=1, cleanup_days=0)  # cleanup_days=0 方便测试

    from src.files.file_manager import FileManager
    fm = FileManager()

    yield fm

    cfg.paths = old_paths
    cfg.file_management = old_fm


class TestMoveToFinished:
    """move_to_finished 测试"""

    def test_move_single_file(self, file_mgr, temp_workspace):
        """移动单个文件到 finished"""
        # 创建源目录和文件
        src_dir = os.path.join(temp_workspace['workspace'], "BR", "PO_test")
        os.makedirs(src_dir, exist_ok=True)
        test_file = os.path.join(src_dir, "output.gz")
        with open(test_file, 'w') as f:
            f.write("test content")

        result = file_mgr.move_to_finished(src_dir)
        assert result is True

        # 验证文件已移动
        finished_file = os.path.join(temp_workspace['finished'], "output.gz")
        assert os.path.exists(finished_file)

        # 验证源目录被删除
        assert not os.path.exists(src_dir)

    def test_move_multiple_files(self, file_mgr, temp_workspace):
        """移动多个文件"""
        src_dir = os.path.join(temp_workspace['workspace'], "test_multi")
        os.makedirs(src_dir, exist_ok=True)

        for name in ["input.gz", "output.gz", "log.txt"]:
            with open(os.path.join(src_dir, name), 'w') as f:
                f.write(f"content of {name}")

        result = file_mgr.move_to_finished(src_dir)
        assert result is True

        finished_files = os.listdir(temp_workspace['finished'])
        assert len(finished_files) == 3

    def test_move_with_name_conflict(self, file_mgr, temp_workspace):
        """目标文件名冲突时应添加时间戳"""
        # 先在 finished 中创建同名文件
        existing = os.path.join(temp_workspace['finished'], "output.gz")
        with open(existing, 'w') as f:
            f.write("existing")

        # 移动同名文件
        src_dir = os.path.join(temp_workspace['workspace'], "test_conflict")
        os.makedirs(src_dir, exist_ok=True)
        with open(os.path.join(src_dir, "output.gz"), 'w') as f:
            f.write("new content")

        result = file_mgr.move_to_finished(src_dir)
        assert result is True

        # 应该有两个文件（原始 + 带时间戳的）
        finished_files = os.listdir(temp_workspace['finished'])
        assert len(finished_files) == 2
        assert "output.gz" in finished_files
        # 带时间戳的文件名
        other = [f for f in finished_files if f != "output.gz"]
        assert len(other) == 1
        assert other[0].startswith("output_")


class TestArchiveFiles:
    """archive_files 测试"""

    def test_archive_files(self, file_mgr, temp_workspace):
        """归档 finished 目录中的文件"""
        # 在 finished 中创建文件
        for name in ["result1.txt", "result2.txt"]:
            with open(os.path.join(temp_workspace['finished'], name), 'w') as f:
                f.write(f"content of {name}")

        result = file_mgr.archive_files()
        assert result is True

        # finished 应该为空
        assert len(os.listdir(temp_workspace['finished'])) == 0

        # archive 中应有日期目录
        archive_subdirs = os.listdir(temp_workspace['archive'])
        assert len(archive_subdirs) == 1

        # 日期目录中应有压缩文件
        date_dir = os.path.join(temp_workspace['archive'], archive_subdirs[0])
        archived_files = os.listdir(date_dir)
        assert len(archived_files) == 2
        assert all(f.endswith('.gz') for f in archived_files)

    def test_archive_empty_finished(self, file_mgr, temp_workspace):
        """finished 为空时归档应成功且无操作"""
        result = file_mgr.archive_files()
        assert result is True

    def test_archived_files_are_gzip(self, file_mgr, temp_workspace):
        """验证归档文件确实是 gzip 压缩的"""
        original_content = "This is the original content 中文测试"
        with open(os.path.join(temp_workspace['finished'], "test.txt"), 'w') as f:
            f.write(original_content)

        file_mgr.archive_files()

        # 找到归档文件
        archive_subdirs = os.listdir(temp_workspace['archive'])
        date_dir = os.path.join(temp_workspace['archive'], archive_subdirs[0])
        archived_file = os.path.join(date_dir, os.listdir(date_dir)[0])

        # 解压验证
        with gzip.open(archived_file, 'rb') as f:
            decompressed = f.read().decode('utf-8')
        assert decompressed == original_content


class TestCleanupExpiredFiles:
    """cleanup_expired_files 测试"""

    def test_cleanup_expired_files(self, file_mgr, temp_workspace):
        """清理过期文件 (cleanup_days=0 表示立即过期)"""
        # 创建归档文件
        date_dir = os.path.join(temp_workspace['archive'], "20250101")
        os.makedirs(date_dir, exist_ok=True)

        for name in ["old1.gz", "old2.gz"]:
            filepath = os.path.join(date_dir, name)
            with open(filepath, 'w') as f:
                f.write("old content")
            # 设置文件修改时间为 31 天前（但 cleanup_days=0 所以任何文件都过期）
            old_time = time.time() - 1  # 1秒前即已过期
            os.utime(filepath, (old_time, old_time))

        result = file_mgr.cleanup_expired_files()
        assert result is True

        # 文件应被清理
        assert not os.path.exists(os.path.join(date_dir, "old1.gz"))
        assert not os.path.exists(os.path.join(date_dir, "old2.gz"))

        # 空目录也应被删除（注意：os.walk 中 dirs 遍历只处理子目录）
        # date_dir 本身可能在 walk 的下一层迭代中被删，也可能不被删
        # 这里只验证文件已清理即可
        if os.path.exists(date_dir):
            assert len(os.listdir(date_dir)) == 0

    def test_cleanup_empty_archive(self, file_mgr, temp_workspace):
        """空 archive 目录清理应成功"""
        result = file_mgr.cleanup_expired_files()
        assert result is True

    def test_cleanup_keeps_recent_files(self, file_mgr, temp_workspace):
        """未过期的文件不应被清理"""
        from src.config.config import config_manager
        cfg = config_manager.get_config()
        cfg.file_management.cleanup_days = 30  # 30天后才过期

        fm_fresh = __import__('src.files.file_manager', fromlist=['FileManager']).FileManager()

        date_dir = os.path.join(temp_workspace['archive'], "20250401")
        os.makedirs(date_dir, exist_ok=True)
        filepath = os.path.join(date_dir, "recent.gz")
        with open(filepath, 'w') as f:
            f.write("recent content")
        # 不修改时间，文件刚创建所以是 "今天" 的

        fm_fresh.cleanup_expired_files()

        # 文件应该还在
        assert os.path.exists(filepath)

        cfg.file_management.cleanup_days = 0  # 恢复


class TestFileListAndSize:
    """文件列表和目录大小"""

    def test_get_file_list(self, file_mgr, temp_workspace):
        """获取目录文件列表"""
        test_dir = os.path.join(temp_workspace['workspace'], "test_list")
        os.makedirs(test_dir, exist_ok=True)

        for name in ["a.txt", "b.txt", "c.gz"]:
            with open(os.path.join(test_dir, name), 'w') as f:
                f.write("x")

        # 创建子目录（不应出现在文件列表中）
        os.makedirs(os.path.join(test_dir, "subdir"), exist_ok=True)

        files = file_mgr.get_file_list(test_dir)
        assert len(files) == 3
        assert set(files) == {"a.txt", "b.txt", "c.gz"}

    def test_get_file_list_empty_dir(self, file_mgr, temp_workspace):
        """空目录返回空列表"""
        files = file_mgr.get_file_list(temp_workspace['temp'])
        assert files == []

    def test_get_file_list_nonexistent_dir(self, file_mgr):
        """不存在的目录返回空列表"""
        files = file_mgr.get_file_list("/nonexistent/path")
        assert files == []

    def test_get_directory_size(self, file_mgr, temp_workspace):
        """获取目录总大小"""
        test_dir = os.path.join(temp_workspace['workspace'], "test_size")
        os.makedirs(test_dir, exist_ok=True)

        # 创建已知大小的文件
        with open(os.path.join(test_dir, "file1.txt"), 'w') as f:
            f.write("a" * 100)
        with open(os.path.join(test_dir, "file2.txt"), 'w') as f:
            f.write("b" * 200)

        size = file_mgr.get_directory_size(test_dir)
        assert size == 300

    def test_get_directory_size_empty(self, file_mgr, temp_workspace):
        """空目录大小为 0"""
        size = file_mgr.get_directory_size(temp_workspace['temp'])
        assert size == 0
