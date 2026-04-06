import os
import shutil
import gzip
import time
import uuid
import logging
import datetime
import threading
from typing import List, Optional
from src.config.config import config_manager

logger = logging.getLogger(__name__)


class FileManager:
    def __init__(self):
        config = config_manager.get_config()
        self.paths = config.paths
        self.file_management = config.file_management
        self._lock = threading.Lock()

    def move_to_finished(self, source_dir: str) -> bool:
        """将优化完成的文件移动至finished文件夹"""
        with self._lock:
            try:
                os.makedirs(self.paths.finished_dir, exist_ok=True)
                files = os.listdir(source_dir)

                for file in files:
                    src_path = os.path.join(source_dir, file)
                    if not os.path.isfile(src_path):
                        continue
                    dst_path = os.path.join(self.paths.finished_dir, file)

                    # 使用 UUID 后缀避免命名冲突（比时间戳更安全）
                    if os.path.exists(dst_path):
                        name, ext = os.path.splitext(file)
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        short_id = uuid.uuid4().hex[:6]
                        new_filename = f"{name}_{timestamp}_{short_id}{ext}"
                        dst_path = os.path.join(self.paths.finished_dir, new_filename)

                    shutil.move(src_path, dst_path)

                # 安全删除空目录
                try:
                    if os.path.isdir(source_dir) and not os.listdir(source_dir):
                        shutil.rmtree(source_dir, ignore_errors=True)
                except OSError:
                    pass

                return True
            except Exception as e:
                logger.error("移动文件失败: %s", e, exc_info=True)
                return False

    def archive_files(self) -> bool:
        """将Finished文件夹中的文件移动至archive文件夹并压缩"""
        with self._lock:
            try:
                os.makedirs(self.paths.archive_dir, exist_ok=True)

                if not os.path.exists(self.paths.finished_dir):
                    return True

                files = os.listdir(self.paths.finished_dir)
                if not files:
                    return True

                archive_date = datetime.datetime.now().strftime("%Y%m%d")
                archive_subdir = os.path.join(self.paths.archive_dir, archive_date)
                os.makedirs(archive_subdir, exist_ok=True)

                for file in files:
                    src_path = os.path.join(self.paths.finished_dir, file)
                    if not os.path.isfile(src_path):
                        continue
                    dst_path = os.path.join(archive_subdir, f"{file}.gz")

                    with open(src_path, 'rb') as f_in:
                        with gzip.open(dst_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)

                    os.remove(src_path)

                logger.info("归档完成，处理 %d 个文件", len(files))
                return True
            except Exception as e:
                logger.error("归档文件失败: %s", e, exc_info=True)
                return False

    def cleanup_expired_files(self) -> bool:
        """清理archive文件夹内超过指定日期的压缩文件"""
        with self._lock:
            try:
                if not os.path.exists(self.paths.archive_dir):
                    return True

                cleanup_days = self.file_management.cleanup_days
                current_time = time.time()
                cleaned_count = 0

                for root, dirs, files in os.walk(self.paths.archive_dir, topdown=False):
                    for file in files:
                        if file.endswith('.gz'):
                            file_path = os.path.join(root, file)
                            file_mtime = os.path.getmtime(file_path)
                            file_age = (current_time - file_mtime) / (24 * 3600)

                            if file_age > cleanup_days:
                                os.remove(file_path)
                                cleaned_count += 1

                    # topdown=False 保证子目录先处理，安全删除空目录
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        try:
                            if not os.listdir(dir_path):
                                os.rmdir(dir_path)
                        except OSError:
                            pass

                if cleaned_count > 0:
                    logger.info("清理过期文件完成，删除 %d 个文件", cleaned_count)
                return True
            except Exception as e:
                logger.error("清理过期文件失败: %s", e, exc_info=True)
                return False

    def get_file_list(self, directory: str) -> List[str]:
        """获取目录中的文件列表"""
        try:
            if not os.path.exists(directory):
                return []

            files = []
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path):
                    files.append(file)

            return files
        except Exception as e:
            logger.error("获取文件列表失败: %s", e)
            return []

    def get_directory_size(self, directory: str) -> int:
        """获取目录大小（字节）"""
        try:
            total_size = 0
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)

            return total_size
        except Exception as e:
            logger.error("获取目录大小失败: %s", e)
            return 0


# 全局文件管理器实例
file_manager = FileManager()
