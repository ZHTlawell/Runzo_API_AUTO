"""
统一断言工具
封装常用断言方法，失败时自动附加详情到 Allure 报告
"""
from __future__ import annotations

import json

import allure
from jsonpath_ng import parse
from jsonschema import validate, ValidationError
from requests import Response

from common.logger import log


class Assertion:
    """统一断言工具类"""

    @staticmethod
    def assert_status_code(response: Response, expected: int):
        """
        断言 HTTP 状态码

        Args:
            response: Response 对象
            expected: 期望的状态码
        """
        actual = response.status_code
        with allure.step(f"断言状态码: 期望={expected}, 实际={actual}"):
            if actual != expected:
                _attach_failure_detail(response, f"状态码不匹配: 期望 {expected}, 实际 {actual}")
            assert actual == expected, (
                f"状态码断言失败: 期望 {expected}, 实际 {actual}\n"
                f"响应内容: {response.text[:500]}"
            )
            log.info(f"断言通过: status_code == {expected}")

    @staticmethod
    def assert_json_path(response: Response, path: str, expected_value):
        """
        断言 JSON 响应中指定路径的值

        Args:
            response: Response 对象
            path: jsonpath 表达式，如 "$.code" 或 "$.data.id"
            expected_value: 期望值
        """
        try:
            json_data = response.json()
        except ValueError:
            raise AssertionError(f"响应不是有效的 JSON: {response.text[:200]}")

        expr = parse(path)
        matches = expr.find(json_data)

        with allure.step(f"断言 JSONPath: {path} == {expected_value}"):
            assert matches, (
                f"JSONPath '{path}' 未匹配到任何数据\n"
                f"响应内容: {json.dumps(json_data, ensure_ascii=False)[:500]}"
            )

            actual_value = matches[0].value
            if actual_value != expected_value:
                _attach_failure_detail(
                    response,
                    f"JSONPath断言失败: {path}\n期望: {expected_value}\n实际: {actual_value}",
                )
            assert actual_value == expected_value, (
                f"JSONPath 断言失败: {path}\n"
                f"期望: {expected_value!r}\n"
                f"实际: {actual_value!r}"
            )
            log.info(f"断言通过: {path} == {expected_value}")

    @staticmethod
    def assert_json_contains(response: Response, path: str, expected_value):
        """
        断言 JSON 中指定路径的值包含期望值（用于字符串或列表）

        Args:
            response: Response 对象
            path: jsonpath 表达式
            expected_value: 期望包含的值
        """
        try:
            json_data = response.json()
        except ValueError:
            raise AssertionError(f"响应不是有效的 JSON: {response.text[:200]}")

        expr = parse(path)
        matches = expr.find(json_data)

        with allure.step(f"断言 JSONPath contains: {path} contains {expected_value}"):
            assert matches, f"JSONPath '{path}' 未匹配到任何数据"
            actual_value = matches[0].value
            assert expected_value in actual_value, (
                f"包含断言失败: {path}\n"
                f"期望包含: {expected_value!r}\n"
                f"实际值: {actual_value!r}"
            )
            log.info(f"断言通过: {path} contains {expected_value}")

    @staticmethod
    def assert_response_time(response: Response, max_ms: int):
        """
        断言响应时间不超过指定毫秒数

        Args:
            response: Response 对象
            max_ms: 最大允许响应时间（毫秒）
        """
        actual_ms = response.elapsed.total_seconds() * 1000
        with allure.step(f"断言响应时间: {actual_ms:.0f}ms <= {max_ms}ms"):
            assert actual_ms <= max_ms, (
                f"响应时间超标: 实际 {actual_ms:.0f}ms > 限制 {max_ms}ms"
            )
            log.info(f"断言通过: 响应时间 {actual_ms:.0f}ms <= {max_ms}ms")

    @staticmethod
    def assert_json_schema(response: Response, schema: dict):
        """
        断言响应 JSON 符合 JSON Schema

        Args:
            response: Response 对象
            schema: JSON Schema 字典
        """
        try:
            json_data = response.json()
        except ValueError:
            raise AssertionError(f"响应不是有效的 JSON: {response.text[:200]}")

        with allure.step("断言 JSON Schema"):
            try:
                validate(instance=json_data, schema=schema)
                log.info("断言通过: JSON Schema 校验成功")
            except ValidationError as e:
                _attach_failure_detail(response, f"Schema校验失败: {e.message}")
                raise AssertionError(f"JSON Schema 校验失败: {e.message}")

    @staticmethod
    def assert_db_record(record: dict | None, expected_fields: dict):
        """
        断言数据库记录的字段值

        Args:
            record: 数据库查询结果（字典）
            expected_fields: 期望的字段值，如 {"username": "test", "status": 1}
        """
        with allure.step(f"断言数据库记录: {expected_fields}"):
            assert record is not None, "数据库记录不存在"

            for field, expected in expected_fields.items():
                actual = record.get(field)
                assert actual == expected, (
                    f"数据库字段断言失败: {field}\n"
                    f"期望: {expected!r}\n"
                    f"实际: {actual!r}"
                )
            log.info(f"断言通过: 数据库记录匹配 {expected_fields}")

    @staticmethod
    def assert_list_length(response: Response, path: str, expected_length: int):
        """
        断言 JSON 中列表的长度

        Args:
            response: Response 对象
            path: jsonpath 表达式（指向列表）
            expected_length: 期望的列表长度
        """
        try:
            json_data = response.json()
        except ValueError:
            raise AssertionError(f"响应不是有效的 JSON: {response.text[:200]}")

        expr = parse(path)
        matches = expr.find(json_data)

        with allure.step(f"断言列表长度: {path} length == {expected_length}"):
            assert matches, f"JSONPath '{path}' 未匹配到任何数据"
            actual_list = matches[0].value
            assert isinstance(actual_list, list), f"{path} 不是列表类型"
            assert len(actual_list) == expected_length, (
                f"列表长度断言失败: {path}\n"
                f"期望长度: {expected_length}\n"
                f"实际长度: {len(actual_list)}"
            )
            log.info(f"断言通过: {path} 长度 == {expected_length}")


def _attach_failure_detail(response: Response, message: str):
    """断言失败时附加详情到 Allure"""
    detail = {
        "error": message,
        "status_code": response.status_code,
        "url": response.url,
        "response_body": response.text[:1000],
    }
    allure.attach(
        json.dumps(detail, ensure_ascii=False, indent=2),
        name="断言失败详情",
        attachment_type=allure.attachment_type.JSON,
    )
