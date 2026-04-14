"""
Locust 性能测试脚本
复用 API 接口定义，支持 Web UI 和命令行两种模式

运行方式：
    Web UI:    locust -f performance/locustfile.py --host=http://test-api.example.com
    命令行:     locust -f performance/locustfile.py --host=http://test-api.example.com \
               --users=100 --spawn-rate=10 --run-time=5m --headless

    也可通过配置文件运行:
    locust -f performance/locustfile.py --config=performance/performance_config.yaml
"""
from locust import HttpUser, between, task


class LoginUser(HttpUser):
    """模拟用户登录场景"""

    wait_time = between(1, 3)

    def on_start(self):
        """每个虚拟用户启动时执行：登录获取 Token"""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        if response.status_code == 200:
            token = response.json().get("data", {}).get("token", "")
            self.client.headers["Authorization"] = f"Bearer {token}"

    @task(5)
    def get_user_info(self):
        """获取用户信息 - 高频接口"""
        self.client.get("/api/v1/user/me")

    @task(3)
    def get_user_list(self):
        """获取用户列表"""
        self.client.get("/api/v1/user/list", params={"page": 1, "size": 10})

    @task(2)
    def get_order_list(self):
        """获取订单列表"""
        self.client.get("/api/v1/order/list", params={"page": 1, "size": 10})

    @task(1)
    def create_order(self):
        """创建订单 - 低频写操作"""
        self.client.post(
            "/api/v1/order/create",
            json={"product_id": "PERF_TEST_001", "quantity": 1},
        )
