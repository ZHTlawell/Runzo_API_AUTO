"""
根级 conftest.py
注册命令行参数、初始化全局配置、加载插件
"""
import pytest

from common.logger import setup_logger
from config.settings import settings


def pytest_addoption(parser):
    """注册自定义命令行参数"""
    parser.addoption(
        "--env",
        action="store",
        default="test",
        help="运行环境: dev/test/staging/prod",
    )


def pytest_configure(config):
    """Pytest 配置阶段，初始化全局设置"""
    env = config.getoption("--env")
    settings.load(env)
    setup_logger(settings.log_level)

    # 注册自定义 markers
    config.addinivalue_line("markers", "smoke: 冒烟测试")
    config.addinivalue_line("markers", "regression: 回归测试")
    config.addinivalue_line("markers", "p0: 最高优先级")
    config.addinivalue_line("markers", "p1: 高优先级")
    config.addinivalue_line("markers", "p2: 中优先级")
    config.addinivalue_line("markers", "p3: 低优先级")
