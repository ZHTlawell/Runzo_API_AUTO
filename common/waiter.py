"""
异步任务等待器

功能说明:
    提供通用的轮询等待机制，用于处理异步接口的状态检查。
    当前主要用于训练计划生成的异步等待：
    - 调用 plan/generate 后，计划在后台异步生成
    - 需要轮询 MongoDB 的 runzo_training-plan 表检查 status 字段
    - status=1 生成中, status=3 成功, status=4 失败

设计思路:
    1. 通用轮询函数：支持任意条件的轮询等待
    2. 计划生成专用等待器：封装 MongoDB 查询逻辑
    3. 超时控制 + 间隔控制 + 详细日志

使用示例:
    from common.waiter import wait_for_plan_ready
    plan_doc = wait_for_plan_ready(mongo_db, user_id, timeout=60, interval=3)
"""
import time
from typing import Callable

import allure

from common.logger import log


def poll_until(
    condition_fn: Callable[[], any],
    timeout: int = 60,
    interval: int = 3,
    desc: str = "等待条件满足",
) -> any:
    """
    通用轮询等待函数

    按固定间隔反复调用 condition_fn，直到它返回「真值」或超时。

    Args:
        condition_fn: 条件函数，返回非 None/False 值表示条件满足
        timeout: 最长等待时间（秒），默认 60 秒
        interval: 轮询间隔（秒），默认 3 秒
        desc: 等待描述（用于日志和 Allure）

    Returns:
        condition_fn 的返回值（条件满足时）

    Raises:
        TimeoutError: 超时未满足条件
    """
    start_time = time.time()
    attempt = 0

    with allure.step(f"轮询等待: {desc} (超时={timeout}s, 间隔={interval}s)"):
        while True:
            attempt += 1
            elapsed = time.time() - start_time

            result = condition_fn()
            if result:
                log.info(
                    f"轮询成功: {desc} | "
                    f"第 {attempt} 次 | 耗时 {elapsed:.1f}s"
                )
                return result

            if elapsed >= timeout:
                log.error(
                    f"轮询超时: {desc} | "
                    f"共 {attempt} 次 | 超时 {timeout}s"
                )
                raise TimeoutError(
                    f"轮询超时({timeout}s): {desc}，共尝试 {attempt} 次"
                )

            log.debug(
                f"轮询中: {desc} | "
                f"第 {attempt} 次 | 已耗时 {elapsed:.1f}s"
            )
            time.sleep(interval)


def wait_for_plan_ready(mongo_db, user_id: str, timeout: int = 120, interval: int = 5):
    """
    等待训练计划生成完成

    轮询 MongoDB 的 runzo_training-plan 集合，检查指定用户的计划生成状态。

    状态说明:
        - status=1: 生成中（继续等待）
        - status=3: 生成成功（返回文档）
        - status=4: 生成失败（抛出异常）

    Args:
        mongo_db: MongoDBHandler 实例
        user_id: 用户ID
        timeout: 最长等待时间（秒），默认 120 秒（计划生成可能较慢）
        interval: 轮询间隔（秒），默认 5 秒

    Returns:
        dict - 计划文档（status=3 时）

    Raises:
        TimeoutError: 超时仍在生成中
        RuntimeError: 计划生成失败（status=4）
    """

    def _check_plan_status():
        """内部条件函数：查询 MongoDB 计划状态"""
        doc = mongo_db.find_one(
            "runzo_training_plan",
            {"createBy": user_id},
        )

        if doc is None:
            log.debug(f"计划文档不存在: createBy={user_id}")
            return None

        status = doc.get("status")

        if status == 3:
            # 生成成功
            log.info(f"计划生成成功: createBy={user_id}, planId={doc.get('_id')}")
            return doc

        if status == 4:
            # 生成失败
            raise RuntimeError(
                f"计划生成失败(status=4): createBy={user_id}, "
                f"doc={doc}"
            )

        # status=1 或其他状态，继续等待
        log.debug(f"计划生成中: createBy={user_id}, status={status}")
        return None

    return poll_until(
        condition_fn=_check_plan_status,
        timeout=timeout,
        interval=interval,
        desc=f"等待计划生成完成 (createBy={user_id})",
    )
