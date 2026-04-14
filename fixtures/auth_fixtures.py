"""
认证相关 Fixtures

功能说明:
    提供测试用例所需的用户认证能力，包括：
    1. auth_user: 会话级 - 设备登录，返回 userId + accessToken
    2. runner_client: 会话级 - 已设置好用户身份头的 HttpClient

    认证流程：
    调用 turing-user-center 的 device-login 接口
    → 生成随机 deviceId 创建新用户
    → 提取 userId 和 accessToken
    → 设置到 turing-runner 的 HttpClient 请求头中

    请求头设置：
    - ts-user-id: 从登录响应中提取的 userId
    - ts-time-zone-id: 从配置文件读取（默认 Asia/Shanghai）
    - ts-country: 从配置文件读取（默认 CN）
    - Authorization: JWT 访问令牌
"""
import pytest

from api.auth_api import AuthAPI
from common.cache import cache
from common.http_client import HttpClient
from common.logger import log
from config.settings import settings


@pytest.fixture(scope="session")
def auth_user(user_center_client):
    """
    会话级别的用户认证

    通过设备登录创建一个测试用户，整个测试会话复用同一个用户。
    返回包含 userId 和 accessToken 的字典。

    Returns:
        dict: {"userId": "xxx", "accessToken": "xxx", "refreshToken": "xxx"}
    """
    auth_api = AuthAPI(user_center_client)

    # 设备登录（自动生成随机 deviceId）
    response = auth_api.device_login()
    assert response.status_code == 200, f"设备登录失败: {response.text}"

    resp_data = response.json()
    assert resp_data.get("code") == 0, f"设备登录业务异常: {resp_data}"

    user_data = resp_data["data"]
    user_id = user_data["userId"]
    access_token = user_data["accessToken"]

    log.info(f"测试用户创建成功: userId={user_id}")

    # 存入全局缓存，供其他模块直接获取
    cache.set("user_id", user_id)
    cache.set("access_token", access_token)

    return {
        "userId": user_id,
        "accessToken": access_token,
        "refreshToken": user_data.get("refreshToken", ""),
    }


@pytest.fixture(scope="session")
def runner_client(auth_user):
    """
    会话级别的 turing-runner HttpClient

    已自动设置好以下请求头：
    - ts-user-id: 当前测试用户ID
    - ts-time-zone-id: 时区
    - ts-country: 国家
    - ts-run-unit: 距离单位
    - Authorization: JWT令牌

    测试用例通过此 client 调用 turing-runner 的所有业务接口。
    """
    client = HttpClient(
        base_url=settings.base_url,
        timeout=settings.timeout,
    )

    # 设置公共请求头（从配置文件读取默认值）
    default_headers = settings.default_headers
    client.set_headers(default_headers)

    # 设置用户身份头
    client.set_headers({
        "ts-user-id": auth_user["userId"],
        "Authorization": f'Bearer {auth_user["accessToken"]}',
    })

    log.info(
        f"Runner HttpClient 已就绪: "
        f"userId={auth_user['userId']}, "
        f"base_url={settings.base_url}"
    )

    yield client
    client.close()
