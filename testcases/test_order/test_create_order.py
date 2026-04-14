"""
创建订单接口测试用例
演示接口上下游依赖：创建订单依赖登录 Token
"""
import allure
import pytest

from common.assertion import Assertion
from common.data_loader import DataLoader

# 加载测试数据
order_data = DataLoader.load("order/create_order.yaml")


@allure.feature("订单管理")
@allure.story("创建订单")
class TestCreateOrder:
    """创建订单测试"""

    @pytest.mark.parametrize(
        "case_data",
        order_data,
        ids=[d["case_id"] for d in order_data],
    )
    @pytest.mark.regression
    def test_create_order(self, order_api, auth_token, case_data):
        """
        参数化创建订单测试
        auth_token fixture 自动处理登录依赖
        """
        allure.dynamic.title(case_data["title"])
        allure.dynamic.severity(allure.severity_level.NORMAL)

        data = case_data["data"]
        expected = case_data["expected"]

        response = order_api.create_order(
            product_id=data["product_id"],
            quantity=data["quantity"],
        )

        Assertion.assert_status_code(response, expected["status_code"])
        Assertion.assert_json_path(
            response, expected["json_path"], expected["value"]
        )

    @pytest.mark.p0
    @allure.title("创建订单后数据库校验")
    def test_create_order_db_verify(
        self, order_api, auth_token, mongo_db, clean_test_data
    ):
        """创建订单后验证数据库记录"""
        product_id = "PROD_DB_TEST"
        quantity = 3

        response = order_api.create_order(
            product_id=product_id,
            quantity=quantity,
        )

        Assertion.assert_status_code(response, 200)

        # 从响应中获取订单ID
        order_id = response.json().get("data", {}).get("order_id")
        assert order_id, "订单ID返回为空"

        # 注册清理
        clean_test_data.add("orders", {"_id": order_id})

        # 数据库校验
        record = mongo_db.find_one("orders", {"_id": order_id})
        Assertion.assert_db_record(record, {
            "product_id": product_id,
            "quantity": quantity,
        })

    @pytest.mark.p1
    @allure.title("创建订单后查询订单详情")
    def test_create_and_query_order(self, order_api, auth_token):
        """
        接口链路测试：创建订单 -> 查询订单
        演示上下游接口关联
        """
        # Step 1: 创建订单
        create_resp = order_api.create_order(
            product_id="PROD_CHAIN_TEST",
            quantity=1,
        )
        Assertion.assert_status_code(create_resp, 200)

        order_id = create_resp.json().get("data", {}).get("order_id")
        assert order_id, "创建订单未返回 order_id"

        # Step 2: 查询订单详情
        query_resp = order_api.get_order(order_id)
        Assertion.assert_status_code(query_resp, 200)
        Assertion.assert_json_path(query_resp, "$.data.product_id", "PROD_CHAIN_TEST")
