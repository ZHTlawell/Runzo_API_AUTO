"""
MongoDB 数据库操作封装
提供常用的 CRUD 操作，用于测试数据准备和数据库校验
"""
from __future__ import annotations

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from common.logger import log


class MongoDBHandler:
    """MongoDB 操作封装"""

    def __init__(
        self,
        uri: str = "",
        db_name: str = "",
        host: str = "",
        port: int = 27017,
        username: str = "",
        password: str = "",
        auth_source: str = "admin",
    ):
        """
        初始化 MongoDB 连接

        支持两种连接方式：
            1. URI 模式（推荐）：直接传入完整连接字符串
            2. 分字段模式：分别传入 host/port/username/password

        Args:
            uri: MongoDB 连接字符串（优先使用）
            db_name: 数据库名
            host: MongoDB 主机地址
            port: 端口号
            username: 用户名（可选）
            password: 密码（可选）
            auth_source: 认证数据库
        """
        if uri:
            # URI 模式连接
            self.client = MongoClient(uri)
            log.info(f"MongoDB 连接成功 (URI 模式): db={db_name}")
        elif username and password:
            self.client = MongoClient(
                host=host,
                port=port,
                username=username,
                password=password,
                authSource=auth_source,
            )
            log.info(f"MongoDB 连接成功: {host}:{port}/{db_name}")
        else:
            self.client = MongoClient(host=host, port=port)
            log.info(f"MongoDB 连接成功: {host}:{port}/{db_name}")

        self.db: Database = self.client[db_name]

    def get_collection(self, collection_name: str) -> Collection:
        """获取集合对象"""
        return self.db[collection_name]

    def find_one(self, collection: str, query: dict) -> dict | None:
        """
        查询单条记录

        Args:
            collection: 集合名
            query: 查询条件

        Returns:
            匹配的文档，无结果返回 None
        """
        result = self.db[collection].find_one(query)
        log.debug(f"MongoDB find_one({collection}, {query}) => {result is not None}")
        return result

    def find_many(
        self,
        collection: str,
        query: dict,
        limit: int = 0,
        sort: list | None = None,
    ) -> list[dict]:
        """
        查询多条记录

        Args:
            collection: 集合名
            query: 查询条件
            limit: 限制返回数量，0 表示不限制
            sort: 排序条件，如 [("created_at", -1)]

        Returns:
            文档列表
        """
        cursor = self.db[collection].find(query)
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)

        results = list(cursor)
        log.debug(f"MongoDB find_many({collection}, {query}) => {len(results)} records")
        return results

    def insert_one(self, collection: str, document: dict) -> str:
        """
        插入单条记录

        Args:
            collection: 集合名
            document: 文档数据

        Returns:
            插入的文档 ID（字符串）
        """
        result = self.db[collection].insert_one(document)
        doc_id = str(result.inserted_id)
        log.debug(f"MongoDB insert_one({collection}) => {doc_id}")
        return doc_id

    def insert_many(self, collection: str, documents: list[dict]) -> list[str]:
        """
        批量插入记录

        Args:
            collection: 集合名
            documents: 文档列表

        Returns:
            插入的文档 ID 列表
        """
        result = self.db[collection].insert_many(documents)
        doc_ids = [str(oid) for oid in result.inserted_ids]
        log.debug(f"MongoDB insert_many({collection}) => {len(doc_ids)} records")
        return doc_ids

    def update_one(self, collection: str, query: dict, update: dict) -> int:
        """
        更新单条记录

        Args:
            collection: 集合名
            query: 查询条件
            update: 更新内容（需包含 $set 等操作符）

        Returns:
            修改的记录数
        """
        result = self.db[collection].update_one(query, update)
        log.debug(
            f"MongoDB update_one({collection}, {query}) => "
            f"matched={result.matched_count}, modified={result.modified_count}"
        )
        return result.modified_count

    def delete_one(self, collection: str, query: dict) -> int:
        """
        删除单条记录

        Args:
            collection: 集合名
            query: 查询条件

        Returns:
            删除的记录数
        """
        result = self.db[collection].delete_one(query)
        log.debug(f"MongoDB delete_one({collection}, {query}) => {result.deleted_count}")
        return result.deleted_count

    def delete_many(self, collection: str, query: dict) -> int:
        """
        删除多条记录（常用于测试数据清理）

        Args:
            collection: 集合名
            query: 查询条件

        Returns:
            删除的记录数
        """
        result = self.db[collection].delete_many(query)
        log.debug(f"MongoDB delete_many({collection}, {query}) => {result.deleted_count}")
        return result.deleted_count

    def count(self, collection: str, query: dict | None = None) -> int:
        """
        统计记录数

        Args:
            collection: 集合名
            query: 查询条件，None 表示统计全部

        Returns:
            记录数
        """
        query = query or {}
        count = self.db[collection].count_documents(query)
        log.debug(f"MongoDB count({collection}, {query}) => {count}")
        return count

    def close(self):
        """关闭数据库连接"""
        self.client.close()
        log.info("MongoDB 连接已关闭")
