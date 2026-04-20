"""
Jenkins 构建后通知脚本

功能说明:
    解析 Allure 报告结果，发送测试报告摘要到飞书/钉钉/企业微信。
    在 Jenkins Pipeline 的 post 阶段调用。

使用方式:
    python3 scripts/send_notification.py \
        --type feishu \
        --webhook https://open.feishu.cn/open-apis/bot/v2/hook/xxx \
        --allure-dir reports/allure-results \
        --env test \
        --report-url http://jenkins.example.com/job/xxx/allure

参数说明:
    --type: 通知类型（feishu/dingtalk/wecom）
    --webhook: Webhook URL
    --allure-dir: Allure 结果目录
    --env: 运行环境
    --report-url: Allure 报告链接（Jenkins Allure 插件生成）
"""
import argparse
import json
import os
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.notify import send_test_report_notification


def parse_allure_results(allure_dir: str) -> dict:
    """
    解析 Allure 结果目录，提取测试统计数据

    Args:
        allure_dir: Allure 结果文件目录

    Returns:
        dict: {"total", "passed", "failed", "error", "duration", "failed_cases"}
    """
    result_dir = Path(allure_dir)
    if not result_dir.exists():
        return {"total": 0, "passed": 0, "failed": 0, "error": 0, "duration": "N/A", "failed_cases": ""}

    total = 0
    passed = 0
    failed = 0
    error = 0
    failed_cases = []
    total_duration_ms = 0

    for f in result_dir.glob("*-result.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)

            total += 1
            status = data.get("status", "")
            name = data.get("name", "unknown")
            start = data.get("start", 0)
            stop = data.get("stop", 0)

            if stop > start:
                total_duration_ms += stop - start

            if status == "passed":
                passed += 1
            elif status == "failed":
                failed += 1
                failed_cases.append(f"• {name}")
            elif status == "broken":
                error += 1
                failed_cases.append(f"• {name} (error)")
        except Exception:
            continue

    # 格式化耗时
    total_sec = total_duration_ms // 1000
    minutes = total_sec // 60
    seconds = total_sec % 60
    duration = f"{minutes}m {seconds}s"

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "error": error,
        "duration": duration,
        "failed_cases": "\n".join(failed_cases[:10]),  # 最多显示10条
    }


def main():
    parser = argparse.ArgumentParser(description="发送测试报告通知")
    parser.add_argument("--type", required=True, choices=["feishu", "dingtalk", "wecom"], help="通知类型")
    parser.add_argument("--webhook", required=True, help="Webhook URL")
    parser.add_argument("--allure-dir", default="reports/allure-results", help="Allure 结果目录")
    parser.add_argument("--env", default="test", help="运行环境")
    parser.add_argument("--report-url", default="", help="Allure 报告链接")
    args = parser.parse_args()

    # 解析结果
    stats = parse_allure_results(args.allure_dir)

    print(f"测试统计: total={stats['total']}, passed={stats['passed']}, "
          f"failed={stats['failed']}, error={stats['error']}, duration={stats['duration']}")

    # 发送通知
    send_test_report_notification(
        notifier_type=args.type,
        webhook_url=args.webhook,
        title=f"Runzo API 自动化测试 [{args.env}]",
        total=stats["total"],
        passed=stats["passed"],
        failed=stats["failed"],
        error=stats["error"],
        duration=stats["duration"],
        report_url=args.report_url,
        env=args.env,
        failed_cases=stats["failed_cases"],
    )


if __name__ == "__main__":
    main()
