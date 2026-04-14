"""
用户模块接口
"""
import allure

from api.base_api import BaseAPI


class UserAPI(BaseAPI):
    """用户相关接口"""

    PREFIX = "/api/v1/user"

    @allure.step("用户注册")
    def register(self, username: str, password: str, email: str, **kwargs):
        payload = {
            "username": username,
            "password": password,
            "email": email,
            **kwargs,
        }
        return self.client.post(f"{self.PREFIX}/register", json=payload)

    @allure.step("获取用户信息")
    def get_user_info(self, user_id: str):
        return self.client.get(f"{self.PREFIX}/{user_id}")

    @allure.step("更新用户信息")
    def update_user(self, user_id: str, **kwargs):
        return self.client.put(f"{self.PREFIX}/{user_id}", json=kwargs)

    @allure.step("删除用户")
    def delete_user(self, user_id: str):
        return self.client.delete(f"{self.PREFIX}/{user_id}")

    @allure.step("获取用户列表")
    def get_user_list(self, page: int = 1, size: int = 10):
        return self.client.get(
            f"{self.PREFIX}/list",
            params={"page": page, "size": size},
        )
