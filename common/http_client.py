"""
HTTP请求二次封装
基于 requests.Session，统一管理请求头、超时、日志、Allure附件
"""
from __future__ import annotations

import json as json_lib

import allure
import requests
from requests import Response

from common.logger import log


class HttpClient:
    """HTTP客户端封装"""

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def set_headers(self, headers: dict):
        """设置全局请求头"""
        self.session.headers.update(headers)

    def set_token(self, token: str):
        """设置认证Token"""
        self.session.headers["Authorization"] = f"Bearer {token}"

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        data: dict | None = None,
        headers: dict | None = None,
        files: dict | None = None,
        **kwargs,
    ) -> Response:
        """
        统一请求方法

        Args:
            method: HTTP方法（GET/POST/PUT/DELETE/PATCH）
            url: 接口路径（相对路径，如 /api/v1/user/login）
            params: URL查询参数
            json: JSON请求体
            data: 表单请求体
            headers: 额外请求头
            files: 文件上传
            **kwargs: requests 其他参数

        Returns:
            Response 对象
        """
        full_url = self.base_url + url
        kwargs.setdefault("timeout", self.timeout)

        # 记录请求日志
        log.info(f">>> {method.upper()} {full_url}")
        if params:
            log.debug(f"    Params: {params}")
        if json:
            log.debug(f"    JSON Body: {json_lib.dumps(json, ensure_ascii=False)}")
        if data:
            log.debug(f"    Form Data: {data}")

        try:
            response = self.session.request(
                method=method,
                url=full_url,
                params=params,
                json=json,
                data=data,
                headers=headers,
                files=files,
                **kwargs,
            )

            # 记录响应日志
            log.info(
                f"<<< {response.status_code} | "
                f"{response.elapsed.total_seconds():.3f}s | "
                f"{method.upper()} {url}"
            )
            log.debug(f"    Response: {_truncate(response.text, 500)}")

            # Allure 附件：请求详情
            _attach_to_allure(method, full_url, params, json, data, response)

            return response

        except requests.exceptions.Timeout:
            log.error(f"请求超时: {method.upper()} {full_url}")
            raise
        except requests.exceptions.ConnectionError:
            log.error(f"连接失败: {method.upper()} {full_url}")
            raise
        except requests.exceptions.RequestException as e:
            log.error(f"请求异常: {method.upper()} {full_url} | {e}")
            raise

    def get(self, url: str, params: dict | None = None, **kwargs) -> Response:
        return self.request("GET", url, params=params, **kwargs)

    def post(
        self,
        url: str,
        json: dict | None = None,
        data: dict | None = None,
        **kwargs,
    ) -> Response:
        return self.request("POST", url, json=json, data=data, **kwargs)

    def put(self, url: str, json: dict | None = None, **kwargs) -> Response:
        return self.request("PUT", url, json=json, **kwargs)

    def delete(self, url: str, **kwargs) -> Response:
        return self.request("DELETE", url, **kwargs)

    def patch(self, url: str, json: dict | None = None, **kwargs) -> Response:
        return self.request("PATCH", url, json=json, **kwargs)

    def close(self):
        """关闭会话"""
        self.session.close()


def _truncate(text: str, max_length: int = 500) -> str:
    """截断过长文本"""
    if len(text) > max_length:
        return text[:max_length] + "...(truncated)"
    return text


def _attach_to_allure(
    method: str,
    url: str,
    params: dict | None,
    json: dict | None,
    data: dict | None,
    response: Response,
):
    """将请求和响应详情附加到 Allure 报告"""
    # 请求详情
    request_info = {
        "method": method.upper(),
        "url": url,
        "headers": dict(response.request.headers),
    }
    if params:
        request_info["params"] = params
    if json:
        request_info["body"] = json
    if data:
        request_info["form_data"] = data

    allure.attach(
        json_lib.dumps(request_info, ensure_ascii=False, indent=2),
        name="请求详情",
        attachment_type=allure.attachment_type.JSON,
    )

    # 响应详情
    response_info = {
        "status_code": response.status_code,
        "elapsed": f"{response.elapsed.total_seconds():.3f}s",
        "headers": dict(response.headers),
    }
    try:
        response_info["body"] = response.json()
    except ValueError:
        response_info["body"] = _truncate(response.text)

    allure.attach(
        json_lib.dumps(response_info, ensure_ascii=False, indent=2),
        name="响应详情",
        attachment_type=allure.attachment_type.JSON,
    )
