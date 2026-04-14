"""
用户认证模块接口

功能说明:
    封装 turing-user-center 服务的认证相关接口。
    当前系统使用「设备登录」方式认证：
    - 通过 deviceId 创建匿名用户
    - 返回 userId 和 accessToken
    - 后续请求通过 Header(ts-user-id) 标识用户身份

服务地址:
    与 turing-runner 不同，认证接口在 turing-user-center 服务上。
    base_url 示例: https://tsapiv1-test.shasoapp.com/turing-user-center

接口清单:
    - device_login: 设备登录，生成用户ID和Token
"""
from __future__ import annotations

import uuid

import allure

from api.base_api import BaseAPI


class AuthAPI(BaseAPI):
    """
    用户认证接口

    该类使用独立的 HttpClient 实例（指向 user-center 服务），
    与业务接口（指向 turing-runner 服务）的 HttpClient 分开。
    """

    @allure.step("设备登录 - 生成用户ID和Token")
    def device_login(self, device_id: str | None = None, app_name: str = "RunnerAI"):
        """
        设备登录接口

        通过设备ID创建匿名用户，获取 userId 和 accessToken。
        每个不同的 deviceId 会创建一个新用户。

        Args:
            device_id: 设备唯一标识，为空则自动生成UUID
            app_name: 应用名称，固定为 "RunnerAI"

        Returns:
            Response 对象，成功时 data 包含:
                - userId: 用户ID（后续作为 ts-user-id 请求头）
                - accessToken: JWT访问令牌
                - refreshToken: JWT刷新令牌
                - expiresIn: 访问令牌有效期（秒）

        请求示例:
            POST /v1/auth/device-login
            {
                "appName": "RunnerAI",
                "deviceId": "5E6443D7-F4D7-408D-B212-660873019F4F",
                "appsflyerId": ""
            }

        响应示例:
            {
                "code": 0,
                "msg": "操作成功",
                "data": {
                    "userId": "95377812116000116",
                    "accessToken": "eyJ0eXAi...",
                    ...
                }
            }
        """
        if device_id is None:
            device_id = str(uuid.uuid4()).upper()

        return self.client.post(
            "/v1/auth/device-login",
            json={
                "appName": app_name,
                "deviceId": device_id,
                "appsflyerId": "",
            },
        )
