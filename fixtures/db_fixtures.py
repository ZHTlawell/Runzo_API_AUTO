"""
数据库相关 Fixtures
提供 MongoDB 连接和数据清理
"""
import pytest

from common.db_handler import MongoDBHandler
from config.settings import settings


@pytest.fixture(scope="session")
def mongo_db():
    """
    会话级别的 MongoDB 连接
    整个测试会话复用同一个连接
    """
    mongo_config = settings.mongodb
    db = MongoDBHandler(
        uri=mongo_config.get("uri", ""),
        db_name=mongo_config.get("db_name", ""),
        host=mongo_config.get("host", ""),
        port=mongo_config.get("port", 27017),
        username=mongo_config.get("username", ""),
        password=mongo_config.get("password", ""),
        auth_source=mongo_config.get("auth_source", "admin"),
    )

    yield db

    db.close()


@pytest.fixture(scope="function")
def clean_test_data(mongo_db):
    """
    函数级别的测试数据清理 Fixture
    测试结束后自动清理带有 auto_test_ 前缀的数据

    用法：
        def test_example(clean_test_data, ...):
            clean_test_data.add("users", {"username": {"$regex": "^auto_test_"}})
            ...  # 测试逻辑
    """

    class CleanupCollector:
        def __init__(self):
            self._cleanups: list[tuple[str, dict]] = []

        def add(self, collection: str, query: dict):
            """注册需要清理的数据"""
            self._cleanups.append((collection, query))

        def execute(self):
            """执行所有清理"""
            for collection, query in self._cleanups:
                mongo_db.delete_many(collection, query)

    collector = CleanupCollector()
    yield collector
    collector.execute()
