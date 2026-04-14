"""
用户注册接口测试用例
"""
import allure
import pytest

from common.assertion import Assertion
from common.data_loader import DataLoader

# 加载测试数据
register_data = DataLoader.load("user/register.yaml")


@allure.feature("用户管理")
@allure.story("用户注册")
class TestUserRegister:
    """用户注册测试"""

    @pytest.mark.parametrize(
        "case_data",
        register_data,
        ids=[d["case_id"] for d in register_data],
    )
    @pytest.mark.smoke
    def test_register(self, user_api, case_data):
        """
        参数化注册测试
        从 register.yaml 读取测试数据，覆盖正常和异常场景
        """
        allure.dynamic.title(case_data["title"])
        allure.dynamic.severity(allure.severity_level.CRITICAL)

        data = case_data["data"]
        expected = case_data["expected"]

        # 调用注册接口
        response = user_api.register(
            username=data["username"],
            password=data["password"],
            email=data["email"],
        )

        # 断言
        Assertion.assert_status_code(response, expected["status_code"])
        Assertion.assert_json_path(
            response, expected["json_path"], expected["value"]
        )

    @pytest.mark.p0
    @allure.title("注册后数据库校验")
    def test_register_db_verify(self, user_api, mongo_db, clean_test_data):
        """
        注册成功后验证数据库中存在对应记录
        """
        username = "auto_test_db_verify_user"
        email = "db_verify@example.com"

        # 注册清理
        clean_test_data.add("users", {"username": username})

        # 调用注册接口
        response = user_api.register(
            username=username,
            password="Test@12345",
            email=email,
        )

        Assertion.assert_status_code(response, 200)

        # 数据库校验
        record = mongo_db.find_one("users", {"username": username})
        Assertion.assert_db_record(record, {
            "username": username,
            "email": email,
        })
