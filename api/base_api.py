"""
API基类
所有业务模块API继承此类
"""
from common.http_client import HttpClient


class BaseAPI:
    """API 基类，持有 HttpClient 实例"""

    def __init__(self, client: HttpClient):
        self.client = client
