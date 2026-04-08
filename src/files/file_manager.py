import os
import shutil
import gzip
import tarfile
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

    def move_to_finished(self, source_dir: str, airline: str, suffix: str = "") -> bool:
        """将任务目录整体移动至 finished/<airline>/ 下，保留子目录结构

        Args:
            source_dir: 源任务工作目录
            airline: 航司代码（作为 finished 子目录名）
            suffix: 可选后缀，追加到目标目录基础名上（例如 "_failed"、"_stop"）
        """
        with self._lock:
            try:
                if not os.path.isdir(source_dir):
                    logger.warning("源目录不存在: %s", source_dir)
                    return False

                airline_finished_dir = os.path.join(self.paths.finished_dir, airline)
                os.makedirs(airline_finished_dir, exist_ok=True)

                base_name = os.path.basename(os.path.normpath(source_dir)) + (suffix or "")
                dst_dir = os.path.join(airline_finished_dir, base_name)

                # 同名冲突时追加时间戳 + 短 UUID
                if os.path.exists(dst_dir):
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    short_id = uuid.uuid4().hex[:6]
                    dst_dir = os.path.join(
                        airline_finished_dir, f"{base_name}_{timestamp}_{short_id}"
                    )

                shutil.move(source_dir, dst_dir)
                logger.info("任务目录已移动至 finished: %s", dst_dir)
                return True
            except Exception as e:
                logger.error("移动任务目录失败: %s", e, exc_info=True)
                return False

    def archive_files(self) -> bool:
        """将 finished 目录中的任务按航司归档至 archive/<airline>/<date>/ 下"""
        with self._lock:
            try:
                os.makedirs(self.paths.archive_dir, exist_ok=True)

                if not os.path.exists(self.paths.finished_dir):
                    return True

                today = datetime.date.today()
                total_archived = 0

                def entry_date(path: str) -> datetime.date:
                    """以 mtime 作为条目所属日期"""
                    return datetime.date.fromtimestamp(os.path.getmtime(path))

                for airline_name in os.listdir(self.paths.finished_dir):
                    airline_src = os.path.join(self.paths.finished_dir, airline_name)
                    if not os.path.isdir(airline_src):
                        # 兼容遗留的顶层散文件（无航司归属），落入 _legacy
                        if os.path.isfile(airline_src):
                            file_date = entry_date(airline_src)
                            if file_date >= today:
                                continue
                            date_str = file_date.strftime("%Y%m%d")
                            legacy_subdir = os.path.join(
                                self.paths.archive_dir, "_legacy", date_str
                            )
                            os.makedirs(legacy_subdir, exist_ok=True)
                            dst = os.path.join(legacy_subdir, f"{airline_name}.gz")
                            with open(airline_src, 'rb') as f_in, gzip.open(dst, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                            os.remove(airline_src)
                            total_archived += 1
                        continue

                    entries = os.listdir(airline_src)
                    if not entries:
                        continue

                    for entry in entries:
                        entry_path = os.path.join(airline_src, entry)
                        try:
                            edate = entry_date(entry_path)
                        except OSError:
                            continue
                        # 当天的条目跳过，留到次日再归档
                        if edate >= today:
                            continue

                        date_str = edate.strftime("%Y%m%d")
                        archive_subdir = os.path.join(
                            self.paths.archive_dir, airline_name, date_str
                        )
                        os.makedirs(archive_subdir, exist_ok=True)

                        if os.path.isdir(entry_path):
                            # 整个任务目录打包为 tar.gz，保留子目录结构
                            dst = os.path.join(archive_subdir, f"{entry}.tar.gz")
                            if os.path.exists(dst):
                                short_id = uuid.uuid4().hex[:6]
                                dst = os.path.join(
                                    archive_subdir, f"{entry}_{short_id}.tar.gz"
                                )
                            with tarfile.open(dst, "w:gz") as tar:
                                tar.add(entry_path, arcname=entry)
                            shutil.rmtree(entry_path, ignore_errors=True)
                            total_archived += 1
                        elif os.path.isfile(entry_path):
                            # 散文件单独 gzip
                            dst = os.path.join(archive_subdir, f"{entry}.gz")
                            with open(entry_path, 'rb') as f_in, gzip.open(dst, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                            os.remove(entry_path)
                            total_archived += 1

                    # 清理空的航司 finished 子目录
                    try:
                        if not os.listdir(airline_src):
                            os.rmdir(airline_src)
                    except OSError:
                        pass

                if total_archived > 0:
                    logger.info("归档完成，处理 %d 个条目", total_archived)
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
