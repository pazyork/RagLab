"""RagLab 日志配置模块"""

import logging
import os
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: str = None,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
) -> None:
    """配置 RagLab 日志系统

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径，默认为 ~/.raglab/logs/raglab.log
        log_format: 日志格式
    """
    # 设置日志级别
    level = getattr(logging, level.upper(), logging.INFO)

    # 配置根 logger
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[]
    )

    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(console_handler)

    # 如果指定了日志文件，添加文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)

    # 设置 RagLab 模块的日志级别
    for name in ["raglab"]:
        logging.getLogger(name).setLevel(level)


def get_logger(name: str = None) -> logging.Logger:
    """获取 RagLab logger

    Args:
        name: Logger 名称，默认为 raglab

    Returns:
        logging.Logger: logger 实例
    """
    return logging.getLogger(name or "raglab")