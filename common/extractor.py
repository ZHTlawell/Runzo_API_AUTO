"""
接口响应数据提取器
使用 jsonpath 从响应中提取指定字段
"""
from jsonpath_ng import parse
from requests import Response

from common.logger import log


class Extractor:
    """响应数据提取工具"""

    @staticmethod
    def extract(response: Response, path: str, index: int = 0):
        """
        使用 jsonpath 从响应中提取数据

        Args:
            response: requests Response 对象
            path: jsonpath 表达式，如 "$.data.token"
            index: 匹配多个结果时取第几个，默认取第一个

        Returns:
            提取到的值，未匹配到返回 None
        """
        try:
            json_data = response.json()
        except ValueError:
            log.error("响应不是有效的 JSON 格式")
            return None

        expr = parse(path)
        matches = expr.find(json_data)

        if not matches:
            log.warning(f"JSONPath '{path}' 未匹配到数据")
            return None

        value = matches[index].value
        log.debug(f"Extracted [{path}] = {value}")
        return value

    @staticmethod
    def extract_all(response: Response, path: str) -> list:
        """
        使用 jsonpath 提取所有匹配的数据

        Args:
            response: requests Response 对象
            path: jsonpath 表达式

        Returns:
            所有匹配值的列表
        """
        try:
            json_data = response.json()
        except ValueError:
            log.error("响应不是有效的 JSON 格式")
            return []

        expr = parse(path)
        matches = expr.find(json_data)
        values = [m.value for m in matches]
        log.debug(f"Extracted all [{path}] = {values}")
        return values

    @staticmethod
    def extract_from_dict(data: dict, path: str, index: int = 0):
        """
        从字典中提取数据（用于非 Response 场景）

        Args:
            data: 字典数据
            path: jsonpath 表达式
            index: 匹配索引

        Returns:
            提取到的值
        """
        expr = parse(path)
        matches = expr.find(data)

        if not matches:
            log.warning(f"JSONPath '{path}' 未匹配到数据")
            return None

        return matches[index].value
