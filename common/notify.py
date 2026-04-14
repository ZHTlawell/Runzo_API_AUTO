"""
测试通知模块
支持钉钉机器人、企业微信机器人、邮件通知
"""
import json
from datetime import datetime

import requests

from common.logger import log


class DingTalkNotifier:
    """钉钉机器人通知"""

    def __init__(self, webhook_url: str, secret: str = ""):
        """
        Args:
            webhook_url: 钉钉机器人 Webhook URL
            secret: 加签密钥（可选）
        """
        self.webhook_url = webhook_url
        self.secret = secret

    def send(
        self,
        title: str,
        total: int,
        passed: int,
        failed: int,
        error: int,
        duration: str,
        report_url: str = "",
    ):
        """
        发送测试报告通知

        Args:
            title: 通知标题
            total: 总用例数
            passed: 通过数
            failed: 失败数
            error: 错误数
            duration: 运行时长
            report_url: 报告链接
        """
        pass_rate = f"{passed / total * 100:.1f}%" if total > 0 else "0%"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        markdown_text = (
            f"### {title}\n\n"
            f"- **执行时间**: {now}\n"
            f"- **总用例数**: {total}\n"
            f"- **通过**: {passed}\n"
            f"- **失败**: {failed}\n"
            f"- **错误**: {error}\n"
            f"- **通过率**: {pass_rate}\n"
            f"- **运行时长**: {duration}\n"
        )
        if report_url:
            markdown_text += f"\n[查看详细报告]({report_url})"

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": markdown_text,
            },
        }

        try:
            resp = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            if resp.status_code == 200:
                log.info("钉钉通知发送成功")
            else:
                log.error(f"钉钉通知发送失败: {resp.text}")
        except Exception as e:
            log.error(f"钉钉通知发送异常: {e}")


class WeComNotifier:
    """企业微信机器人通知"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(
        self,
        title: str,
        total: int,
        passed: int,
        failed: int,
        error: int,
        duration: str,
        report_url: str = "",
    ):
        """发送测试报告通知"""
        pass_rate = f"{passed / total * 100:.1f}%" if total > 0 else "0%"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        content = (
            f"## {title}\n"
            f"> 执行时间: {now}\n"
            f"> 总用例数: <font color=\"info\">{total}</font>\n"
            f"> 通过: <font color=\"info\">{passed}</font>\n"
            f"> 失败: <font color=\"warning\">{failed}</font>\n"
            f"> 错误: <font color=\"comment\">{error}</font>\n"
            f"> 通过率: **{pass_rate}**\n"
            f"> 运行时长: {duration}\n"
        )
        if report_url:
            content += f"\n[查看详细报告]({report_url})"

        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content},
        }

        try:
            resp = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            if resp.status_code == 200:
                log.info("企业微信通知发送成功")
            else:
                log.error(f"企业微信通知发送失败: {resp.text}")
        except Exception as e:
            log.error(f"企业微信通知发送异常: {e}")


def send_test_report_notification(
    notifier_type: str,
    webhook_url: str,
    **kwargs,
):
    """
    统一通知入口

    Args:
        notifier_type: 通知类型 ("dingtalk" / "wecom")
        webhook_url: Webhook URL
        **kwargs: 通知内容参数
    """
    notifiers = {
        "dingtalk": DingTalkNotifier,
        "wecom": WeComNotifier,
    }

    notifier_cls = notifiers.get(notifier_type)
    if not notifier_cls:
        log.error(f"不支持的通知类型: {notifier_type}")
        return

    notifier = notifier_cls(webhook_url)
    notifier.send(**kwargs)
