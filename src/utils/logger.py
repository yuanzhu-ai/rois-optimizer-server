"""
日志管理模块
提供全局日志配置，支持控制台输出和文件轮转
"""
import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler


def setup_logging(log_dir: str = "./logs", log_level: str = "INFO"):
    """
    配置全局日志系统
    
    Args:
        log_dir: 日志文件目录
        log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
    """
    os.makedirs(log_dir, exist_ok=True)

    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 日志格式
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 避免重复添加handler
    if root_logger.handlers:
        return root_logger

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 应用日志文件 - 按天轮转，保留30天
    app_log_path = os.path.join(log_dir, "app.log")
    app_file_handler = TimedRotatingFileHandler(
        app_log_path,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    app_file_handler.setLevel(level)
    app_file_handler.setFormatter(formatter)
    app_file_handler.suffix = "%Y-%m-%d"
    root_logger.addHandler(app_file_handler)

    # 错误日志单独文件 - 按天轮转，保留60天
    error_log_path = os.path.join(log_dir, "error.log")
    error_file_handler = TimedRotatingFileHandler(
        error_log_path,
        when="midnight",
        interval=1,
        backupCount=60,
        encoding="utf-8"
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    error_file_handler.suffix = "%Y-%m-%d"
    root_logger.addHandler(error_file_handler)

    # 降低第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志器"""
    return logging.getLogger(name)
