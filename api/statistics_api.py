"""
跑步统计模块接口

功能说明:
    封装 turing-runner 服务中与训练统计相关的 13 个接口，分为 5 组：

    1. 三大分数体系（Speed 速度 / Endurance 耐力 / Stamina 速度耐力）
       - 前置条件: 必须调用 plan/start-training 校准完成开启训练后才有数据
       - scoreType 可选值: speed / endurance / stamina
    2. 计划进度与概览
    3. 训练统计（周统计、日历状态、跑量趋势、关键训练）
    4. 成绩预测与 VO2Max

依赖关系:
    - 三大分数、跑量趋势、关键训练 → 依赖 planId
    - 日历状态 → 需要 startTimestamp / endTimestamp（毫秒时间戳）
    - 计划概览、VO2Max、成绩预测 → 只需用户有训练记录
"""
from __future__ import annotations

import allure

from api.base_api import BaseAPI


class StatisticsAPI(BaseAPI):
    """
    跑步统计相关接口

    方法按业务分组排列：
    1. 三大分数（Speed/Endurance/Stamina）
    2. 计划进度与概览
    3. 训练统计
    4. 成绩预测与 VO2Max
    """

    PREFIX = "/runzo/statistics"

    # ========== 1. 三大分数体系 ==========

    @allure.step("查询当前三大分数值")
    def scores(self, plan_id: str):
        """
        查询当前三大分数值（Speed/Endurance/Stamina）

        前置条件: 必须先调用 plan/start-training 校准完成开启训练。

        返回内容:
            - focusScore: 当前专注提升的分数类型
            - speed: 速度分数（含当前分、预测区间、配速区间）
            - endurance: 耐力分数
            - stamina: 速度耐力分数

        Args:
            plan_id: 训练计划ID

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/scores",
            json={"trainingPlanId": plan_id},
        )

    @allure.step("查询三大分数子项得分情况")
    def scores_item(self, plan_id: str, score_type: str):
        """
        查询指定分数类型的子项详情

        Args:
            plan_id: 训练计划ID
            score_type: 分数类型，可选值:
                - "speed": 速度得分
                - "endurance": 耐力得分
                - "stamina": 速度耐力得分

        Returns:
            Response 对象，包含子项得分、趋势、专注训练计划
        """
        return self.client.post(
            f"{self.PREFIX}/scores/item",
            json={"trainingPlanId": plan_id, "scoreType": score_type},
        )

    @allure.step("查询三大分数变动趋势")
    def scores_trend(self, plan_id: str, days: int = 30):
        """
        查询三大分数的历史变动趋势

        Args:
            plan_id: 训练计划ID
            days: 查询天数，默认30天

        Returns:
            Response 对象，包含每天的三项分数
        """
        return self.client.post(
            f"{self.PREFIX}/scores/trend",
            json={"trainingPlanId": plan_id, "days": days},
        )

    # ========== 2. 计划进度与概览 ==========

    @allure.step("查询计划概览统计")
    def plan_overview(self):
        """
        查询当前用户训练计划的概览统计

        无需参数，基于用户身份返回。

        Returns:
            Response 对象
        """
        return self.client.get(f"{self.PREFIX}/plan-overview")

    @allure.step("查询用户计划进度")
    def plan_progress(self):
        """
        查询用户计划的 progress

        Returns:
            Response 对象
        """
        return self.client.get(f"{self.PREFIX}/plan-progress")

    @allure.step("查询当前用户计划进度概览")
    def plan_progress_detail(self):
        """
        查询当前用户计划进度概览（更详细的版本）

        Returns:
            Response 对象
        """
        return self.client.get(f"{self.PREFIX}/plan/progress")

    # ========== 3. 训练统计 ==========

    @allure.step("查询周的训练统计")
    def current_week(self, day_start_time: int | None = None):
        """
        查询本周的训练统计数据

        Args:
            day_start_time: 指定日期的开始时间戳（毫秒），为空则默认本周

        Returns:
            Response 对象
        """
        payload = {}
        if day_start_time is not None:
            payload["dayStartTime"] = day_start_time
        return self.client.post(f"{self.PREFIX}/current-week", json=payload)

    @allure.step("查询日历训练状态")
    def calendar_status(self, start_timestamp: int, end_timestamp: int):
        """
        查询指定时间范围内的日历训练状态

        用于日历视图展示每天的训练完成情况。

        Args:
            start_timestamp: 起始时间戳（毫秒）
            end_timestamp: 结束时间戳（毫秒）

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/calendar-status",
            json={
                "startTimestamp": start_timestamp,
                "endTimestamp": end_timestamp,
            },
        )

    @allure.step("查询实际跑量和推荐跑量趋势")
    def distance_trend(self, plan_id: str, data_dimension: str = "day", days: int = 30):
        """
        查询实际跑量 vs 推荐跑量的趋势对比

        Args:
            plan_id: 训练计划ID
            data_dimension: 数据维度
                - "day": 按天返回
                - "week": 按周聚合返回
            days: 查询天数，默认30天

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/distance/trend",
            json={
                "trainingPlanId": plan_id,
                "dataDimension": data_dimension,
                "days": days,
            },
        )

    @allure.step("查询本周关键训练情况")
    def key_sessions_current_week(self, plan_id: str):
        """
        查询本周的关键训练（Key Sessions）完成情况

        Args:
            plan_id: 训练计划ID

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/key-sessions/current-week",
            json={"trainingPlanId": plan_id},
        )

    @allure.step("查询训练总览")
    def training_session_overview(self):
        """
        查询训练 session 概览

        Returns:
            Response 对象
        """
        return self.client.get(f"{self.PREFIX}/training-session-overview")

    # ========== 4. 成绩预测与 VO2Max ==========

    @allure.step("查询成绩预测")
    def race_prediction(self):
        """
        查询用户的比赛成绩预测

        Returns:
            Response 对象
        """
        return self.client.get(f"{self.PREFIX}/race-prediction")

