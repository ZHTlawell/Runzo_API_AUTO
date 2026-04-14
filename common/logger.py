"""
日志管理模块
基于 loguru，支持控制台 + 文件双输出，按天轮转，自动清理
"""
import sys
from pathlib import Path

from loguru import logger

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


def setup_logger(level: str = "INFO"):
    """
    初始化日志配置

    Args:
        level: 日志级别（DEBUG/INFO/WARNING/ERROR）
    """
    # 移除默认 handler
    logger.remove()

    # 控制台输出（彩色）
    logger.add(
        sys.stdout,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # 文件输出（按天轮转，保留7天）
    logger.add(
        str(LOG_DIR / "{time:YYYY-MM-DD}.log"),
        level=level,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
        rotation="00:00",
        retention="7 days",
        encoding="utf-8",
    )

    # 错误日志单独记录
    logger.add(
        str(LOG_DIR / "error_{time:YYYY-MM-DD}.log"),
        level="ERROR",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
    )

    return logger


# 导出 logger 实例供其他模块使用
log = logger
