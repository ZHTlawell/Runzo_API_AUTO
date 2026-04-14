"""
全局数据缓存
用于解决接口上下游依赖问题（如登录token传递、接口关联数据）
"""
import threading

from common.logger import log


class DataCache:
    """
    全局数据缓存池（线程安全单例）

    使用场景：
        - 登录接口获取 token，缓存后供后续接口使用
        - 创建资源后缓存 ID，供查询/更新/删除接口使用
        - 任何需要跨用例传递数据的场景

    示例：
        cache = DataCache()
        cache.set("token", "abc123")
        token = cache.get("token")
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._cache = {}
        return cls._instance

    def set(self, key: str, value):
        """存入缓存"""
        self._cache[key] = value
        log.debug(f"Cache SET: {key} = {value}")

    def get(self, key: str, default=None):
        """从缓存获取"""
        value = self._cache.get(key, default)
        log.debug(f"Cache GET: {key} = {value}")
        return value

    def remove(self, key: str):
        """删除缓存项"""
        self._cache.pop(key, None)
        log.debug(f"Cache REMOVE: {key}")

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        log.debug("Cache CLEARED")

    def has(self, key: str) -> bool:
        """检查缓存是否存在"""
        return key in self._cache

    def all(self) -> dict:
        """获取所有缓存数据"""
        return self._cache.copy()


# 全局缓存实例
cache = DataCache()
