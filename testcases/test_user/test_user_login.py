"""
用户登录接口测试用例
"""
import allure
import pytest

from common.assertion import Assertion
from common.cache import cache
from common.data_loader import DataLoader
from common.extractor import Extractor

# 加载测试数据
login_data = DataLoader.load("user/login.yaml")


@allure.feature("用户管理")
@allure.story("用户登录")
class TestUserLogin:
    """用户登录测试"""

    @pytest.mark.parametrize(
        "case_data",
        login_data,
        ids=[d["case_id"] for d in login_data],
    )
    @pytest.mark.smoke
    def test_login(self, auth_api, case_data):
        """参数化登录测试"""
        allure.dynamic.title(case_data["title"])
        allure.dynamic.severity(allure.severity_level.CRITICAL)

        data = case_data["data"]
        expected = case_data["expected"]

        response = auth_api.login(
            username=data["username"],
            password=data["password"],
        )

        Assertion.assert_status_code(response, expected["status_code"])
        Assertion.assert_json_path(
            response, expected["json_path"], expected["value"]
        )

    @pytest.mark.p0
    @allure.title("登录成功获取Token并缓存")
    def test_login_and_cache_token(self, auth_api):
        """
        测试登录成功后提取 Token 并存入缓存
        演示接口上下游依赖的处理方式
        """
        response = auth_api.login(username="admin", password="admin123")
        Assertion.assert_status_code(response, 200)

        # 使用 Extractor 提取 Token
        token = Extractor.extract(response, "$.data.token")
        assert token, "Token 提取失败"

        # 存入全局缓存，供下游接口使用
        cache.set("login_token", token)
        assert cache.has("login_token")

    @pytest.mark.p1
    @allure.title("登录接口响应时间校验")
    def test_login_response_time(self, auth_api):
        """验证登录接口响应时间在可接受范围内"""
        response = auth_api.login(username="admin", password="admin123")

        # 断言响应时间不超过 3 秒
        Assertion.assert_response_time(response, max_ms=3000)
