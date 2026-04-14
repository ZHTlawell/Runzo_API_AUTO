"""
测试用例层 conftest.py

功能说明:
    为所有测试用例提供公共的 Pytest Fixtures，包括：
    1. HTTP 客户端（user_center_client / runner_client）
    2. API 对象（plan_api / auth_api 等）
    3. 数据库连接（mongo_db）
    4. 认证信息（auth_user）

    通过 Fixture 的依赖注入机制，测试用例只需声明参数即可获取所需资源，
    无需手动初始化连接、设置请求头等。

Fixture 依赖链:
    user_center_client → auth_user → runner_client → plan_api / workout_api ...
                                  ↘ mongo_db (独立)

Scope 说明:
    - session 级: HTTP客户端、认证信息、DB连接（整个会话复用）
    - function 级: 数据清理（每个用例独立）
"""
import pytest

from api.plan_api import PlanAPI
from api.settlement_api import SettlementAPI
from api.statistics_api import StatisticsAPI
from api.workout_api import WorkoutAPI
from common.http_client import HttpClient
from config.settings import settings

# 导入外部 fixtures 以便 pytest 自动发现
from fixtures.auth_fixtures import *  # noqa: F401, F403
from fixtures.db_fixtures import *  # noqa: F401, F403


@pytest.fixture(scope="session")
def user_center_client():
    """
    会话级别的 turing-user-center HttpClient

    专门用于调用用户认证服务（device-login 等）。
    与 runner_client 指向不同的服务地址。
    """
    client = HttpClient(
        base_url=settings.user_center_url,
        timeout=settings.timeout,
    )
    yield client
    client.close()


@pytest.fixture(scope="session")
def http_client(runner_client):
    """
    通用 HTTP 客户端别名

    指向 runner_client，保持与旧用例的兼容性。
    新用例推荐直接使用 runner_client。
    """
    return runner_client


@pytest.fixture(scope="session")
def plan_api(runner_client):
    """
    训练计划模块 API

    已包含用户认证头，可直接调用计划相关的所有接口。
    """
    return PlanAPI(runner_client)


@pytest.fixture(scope="session")
def workout_api(runner_client):
    """
    跑步训练模块 API

    已包含用户认证头，可直接调用训练相关的所有接口。
    """
    return WorkoutAPI(runner_client)


@pytest.fixture(scope="session")
def settlement_api(runner_client):
    """
    跑步结算模块 API

    已包含用户认证头，可直接调用结算相关的所有接口。
    """
    return SettlementAPI(runner_client)


@pytest.fixture(scope="session")
def statistics_api(runner_client):
    """
    跑步统计模块 API

    已包含用户认证头，可直接调用统计相关的所有接口。
    """
    return StatisticsAPI(runner_client)
