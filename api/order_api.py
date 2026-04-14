"""
订单模块接口（示例）
"""
import allure

from api.base_api import BaseAPI


class OrderAPI(BaseAPI):
    """订单相关接口"""

    PREFIX = "/api/v1/order"

    @allure.step("创建订单")
    def create_order(self, product_id: str, quantity: int, **kwargs):
        payload = {
            "product_id": product_id,
            "quantity": quantity,
            **kwargs,
        }
        return self.client.post(f"{self.PREFIX}/create", json=payload)

    @allure.step("查询订单详情")
    def get_order(self, order_id: str):
        return self.client.get(f"{self.PREFIX}/{order_id}")

    @allure.step("取消订单")
    def cancel_order(self, order_id: str, reason: str = ""):
        return self.client.post(
            f"{self.PREFIX}/{order_id}/cancel",
            json={"reason": reason},
        )

    @allure.step("获取订单列表")
    def get_order_list(self, page: int = 1, size: int = 10, status: str = ""):
        params = {"page": page, "size": size}
        if status:
            params["status"] = status
        return self.client.get(f"{self.PREFIX}/list", params=params)
