"""
跑步结算模块接口

功能说明:
    封装 turing-runner 服务中与训练结算相关的 47 个接口。
    结算模块是训练结束后的数据分析核心，涵盖：
    - 训练日志管理（查询/上传/更新）
    - 配速数据分析
    - 心率数据与区间分布
    - 跑步经济性 / EF 有氧得分
    - 跑姿分析
    - 教练来信
    - 成绩预测与完赛预估
    - 计划调整建议（SFS）
    - 每公里表现 / 海拔

业务链路:
    workout/end → log/status(等待日志生成) → log/details(获取logId)
    → 配速/心率/经济性/跑姿/教练来信/成绩预测...（全部依赖logId）

关键依赖:
    - 几乎所有接口都依赖 logId（从 log/status 或 daily/logs 获取）
    - 教练来信依赖 dailyId
    - 竞赛总结依赖 trainingPlanId
"""
from __future__ import annotations

import allure

from api.base_api import BaseAPI


class SettlementAPI(BaseAPI):
    """
    跑步结算相关接口

    方法按业务分组排列：
    1. 训练日志
    2. 配速数据
    3. 心率数据
    4. 跑步经济性 / EF 得分
    5. 跑姿分析
    6. 教练来信
    7. 成绩预测
    8. 计划调整（SFS）
    9. 每公里表现 / 海拔
    10. 训练评价 / 提升训练
    """

    PREFIX = "/runzo/settlement"

    # ========== 1. 训练日志 ==========

    @allure.step("查询用户上传log状态")
    def log_status(self, log_id: str):
        """
        查询训练日志的生成状态

        训练结束后，服务端异步生成日志。通过此接口轮询状态。

        Args:
            log_id: 训练日志ID

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/log/status",
            json={"logId": log_id},
        )

    @allure.step("查询日志是否已完整生成")
    def log_ready(self, log_id: str):
        """
        查询日志是否已完整生成（包含训练反馈、调整计划）

        比 log_status 更严格：不仅日志存在，还要反馈和计划调整全部生成完毕。

        Args:
            log_id: 训练日志ID

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/log/ready",
            json={"logId": log_id},
        )

    @allure.step("获取训练日志详情")
    def log_details(self, log_id: str):
        """
        获取训练日志的完整详情

        包含配速、心率、距离、时长、轨迹等全量训练数据。

        Args:
            log_id: 训练日志ID

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/log/details",
            json={"logId": log_id},
        )

    @allure.step("查询日跑步计划所有训练log")
    def daily_logs(self, daily_id: str):
        """
        查询指定日计划下的所有训练日志

        一个日计划可能有多次训练记录（如中止后重新跑）。

        Args:
            daily_id: 日计划ID

        Returns:
            Response 对象，data 中包含 logId 列表
        """
        return self.client.post(
            f"{self.PREFIX}/daily/logs",
            json={"dailyId": daily_id},
        )

    @allure.step("更新日训练对应的log")
    def daily_log_modify(self, daily_id: str, training_log_id: str):
        """
        更新日计划关联的训练日志

        Args:
            daily_id: 日计划ID
            training_log_id: 训练日志ID
        """
        return self.client.post(
            f"{self.PREFIX}/daily/log/modify",
            json={"dailyId": daily_id, "trainingLogId": training_log_id},
        )

    @allure.step("获取训练分享日志详情")
    def share_log_details(self, log_id: str):
        """获取用于分享的训练日志详情"""
        return self.client.post(
            f"{self.PREFIX}/share-log/details",
            json={"logId": log_id},
        )

    @allure.step("手表上传训练log")
    def watch_settle(self, settle_data: dict):
        """
        手表端上传训练log（含完整训练数据）

        Args:
            settle_data: 完整的手表训练数据（字段较多，直接传字典）
        """
        return self.client.post(f"{self.PREFIX}/watch-settle", json=settle_data)

    @allure.step("上传手表操作日志")
    def watch_log(self, log_time: int, operate: str):
        """上传手表操作日志"""
        return self.client.post(
            f"{self.PREFIX}/watch-log",
            json={"logTime": log_time, "operate": operate},
        )

    # ========== 2. 配速数据 ==========

    @allure.step("获取训练配速")
    def pace(self, log_id: str):
        """获取整体训练配速曲线"""
        return self.client.get(f"{self.PREFIX}/pace", params={"logId": log_id})

    @allure.step("获取训练配速区间达标情况")
    def pace_range_zone(self, log_id: str):
        """获取配速区间达标分析"""
        return self.client.post(
            f"{self.PREFIX}/pace/range-zone",
            json={"logId": log_id},
        )

    @allure.step("获取间歇跑训练配速")
    def pace_interval(self, log_id: str):
        """获取间歇跑各段配速数据"""
        return self.client.get(f"{self.PREFIX}/pace/interval", params={"logId": log_id})

    @allure.step("获取间歇跑训练配速达标情况")
    def pace_interval_qualified(self, log_id: str):
        """获取间歇跑配速达标分析"""
        return self.client.get(
            f"{self.PREFIX}/pace/interval/qualified", params={"logId": log_id}
        )

    # ========== 3. 心率数据 ==========

    @allure.step("获取训练心率")
    def heart_rate(self, log_id: str):
        """获取整体训练心率曲线"""
        return self.client.get(f"{self.PREFIX}/heart-rate", params={"logId": log_id})

    @allure.step("获取训练心率区间分布")
    def heart_rate_zone(self, log_id: str):
        """获取心率在各区间（Z1-Z5）的分布情况"""
        return self.client.post(
            f"{self.PREFIX}/heart-rate-zone",
            json={"logId": log_id},
        )

    @allure.step("获取心率区间细分")
    def heart_rate_zone_breakdown(self, log_id: str):
        """获取心率区间的详细细分数据"""
        return self.client.get(
            f"{self.PREFIX}/heart-rate/zone-breakdown", params={"logId": log_id}
        )

    @allure.step("获取间歇跑心率数据")
    def heart_rate_interval(self, log_id: str):
        """获取间歇跑各段心率"""
        return self.client.get(
            f"{self.PREFIX}/heart-rate/interval", params={"logId": log_id}
        )

    @allure.step("获取间歇跑工作段心率详情")
    def heart_rate_interval_segments(self, log_id: str):
        """获取间歇跑每个工作段的心率详情"""
        return self.client.get(
            f"{self.PREFIX}/heart-rate/interval/segments", params={"logId": log_id}
        )

    # ========== 4. 跑步经济性 / EF 得分 ==========

    @allure.step("获取本次训练跑步经济性得分")
    def running_economy_score(self, log_id: str):
        """获取本次训练的跑步经济性（RE）得分"""
        return self.client.post(
            f"{self.PREFIX}/running-economy/score",
            json={"logId": log_id},
        )

    @allure.step("获取本周跑步经济性得分")
    def running_economy_weekly(self, log_id: str):
        """获取本周的跑步经济性得分"""
        return self.client.post(
            f"{self.PREFIX}/running-economy/weekly",
            json={"logId": log_id},
        )

    @allure.step("获取近7次跑步经济性得分")
    def running_economy_last7(self, log_id: str):
        """获取近7次训练的跑步经济性得分趋势"""
        return self.client.post(
            f"{self.PREFIX}/running-economy/last7count",
            json={"logId": log_id},
        )

    @allure.step("获取跑步经济性得分分析")
    def running_economy_analysis(self, log_id: str):
        """获取跑步经济性的详细分析"""
        return self.client.post(
            f"{self.PREFIX}/running-economy/analysis",
            json={"logId": log_id},
        )

    @allure.step("获取指定天数的跑步经济性得分")
    def running_economy(self, log_id: str, days: int = 7):
        """获取指定天数范围内的跑步经济性得分"""
        return self.client.post(
            f"{self.PREFIX}/running-economy",
            json={"logId": log_id, "days": days},
        )

    @allure.step("获取本次训练有氧得分(EF)")
    def ef_score(self, log_id: str):
        """获取本次训练的 EF（Efficiency Factor）有氧得分"""
        return self.client.post(
            f"{self.PREFIX}/ef/score",
            json={"logId": log_id},
        )

    @allure.step("获取近7次EF表现数据")
    def ef_last7(self, log_id: str):
        """获取近7次训练的 EF 得分趋势"""
        return self.client.post(
            f"{self.PREFIX}/ef/last7count",
            json={"logId": log_id},
        )

    @allure.step("获取训练EF表现")
    def ef_performance(self, log_id: str):
        """获取 EF 表现详情"""
        return self.client.get(
            f"{self.PREFIX}/ef-performance", params={"logId": log_id}
        )

    # ========== 5. 跑姿分析 ==========

    @allure.step("获取本次训练跑姿得分")
    def running_posture_score(self, log_id: str):
        """获取本次训练的跑姿综合得分"""
        return self.client.post(
            f"{self.PREFIX}/running-posture/score",
            json={"logId": log_id},
        )

    @allure.step("获取近7次训练跑姿得分")
    def running_posture_last7(self, log_id: str):
        """获取近7次训练的跑姿得分趋势"""
        return self.client.post(
            f"{self.PREFIX}/running-posture/last7count",
            json={"logId": log_id},
        )

    @allure.step("获取近7次跑姿子项得分")
    def running_posture_item_last7(self, log_id: str):
        """获取近7次训练的跑姿各子项（步频、步幅等）得分"""
        return self.client.post(
            f"{self.PREFIX}/running-posture/item-score/last7count",
            json={"logId": log_id},
        )

    @allure.step("获取跑姿改善待办事项")
    def running_posture_improve_todo(self, log_id: str):
        """获取本次训练后的跑姿改善建议"""
        return self.client.post(
            f"{self.PREFIX}/running-posture/improve-todo",
            json={"logId": log_id},
        )

    # ========== 6. 教练来信 ==========

    @allure.step("获取训练后教练来信")
    def coach_letter(self, daily_id: str):
        """获取本次训练后教练的反馈信"""
        return self.client.get(
            f"{self.PREFIX}/coach/letter", params={"dailyId": daily_id}
        )

    @allure.step("获取休息日教练来信")
    def coach_letter_rest(self, daily_id: str):
        """获取休息日的教练来信"""
        return self.client.get(
            f"{self.PREFIX}/coach/letter-rest", params={"dailyId": daily_id}
        )

    @allure.step("标记教练来信已读")
    def coach_letter_viewed(self, letter_id: str):
        """标记训练后的教练来信为已读"""
        return self.client.post(
            f"{self.PREFIX}/coach/letter/viewed",
            json={"letterId": letter_id},
        )

    @allure.step("标记休息日教练来信已读")
    def coach_letter_rest_viewed(self, letter_id: str):
        """标记休息日的教练来信为已读"""
        return self.client.post(
            f"{self.PREFIX}/coach/letter-rest/viewed",
            json={"letterId": letter_id},
        )

    # ========== 7. 成绩预测 ==========

    @allure.step("获取训练实时预测成绩")
    def forecast_finish_time(self, log_id: str):
        """获取基于本次训练数据的实时预测完赛成绩"""
        return self.client.post(
            f"{self.PREFIX}/forecast-finish-time",
            json={"logId": log_id},
        )

    @allure.step("获取本周训练实时预测成绩")
    def forecast_finish_time_weekly(self, log_id: str):
        """获取本周训练汇总的预测完赛成绩"""
        return self.client.post(
            f"{self.PREFIX}/forecast-finish-time/weekly",
            json={"logId": log_id},
        )

    @allure.step("获取本次训练实时预测成绩")
    def progress_tracking(self, log_id: str):
        """获取本次训练的进度追踪和预测成绩"""
        return self.client.post(
            f"{self.PREFIX}/progress/tracking",
            json={"logId": log_id},
        )

    @allure.step("查询用户最新预测成绩状态")
    def predict_status(self):
        """查询用户最新的预测成绩状态"""
        return self.client.get(f"{self.PREFIX}/predict/staus")

    @allure.step("获取用户计划完赛预测成绩")
    def user_pb(self):
        """获取用户训练计划结束后的预测完赛成绩（PB）"""
        return self.client.get(f"{self.PREFIX}/user-pb")

    @allure.step("获取计划训练总结")
    def competition_summary(self, plan_id: str):
        """获取整个训练计划完成后的竞赛总结"""
        return self.client.get(
            f"{self.PREFIX}/competition-summary",
            params={"trainingPlanId": plan_id},
        )

    # ========== 8. 计划调整（SFS） ==========

    @allure.step("获取训练匹配度评分")
    def plan_compatibility(self, log_id: str):
        """获取本次训练与计划的匹配度评分"""
        return self.client.post(
            f"{self.PREFIX}/plan-compatibility",
            json={"logId": log_id},
        )

    @allure.step("获取SFS调整日计划概览")
    def sfs_adjust_plan(self, log_id: str):
        """获取基于 SFS（Smart Feedback System）的计划调整建议"""
        return self.client.post(
            f"{self.PREFIX}/sfs/adjust/plan",
            json={"logId": log_id},
        )

    @allure.step("接受SFS调整日计划")
    def sfs_adjust_plan_accept(self, log_id: str, adjust_type: str = "", intensity: str = ""):
        """接受 SFS 推荐的计划调整方案"""
        payload = {"logId": log_id}
        if adjust_type:
            payload["adjustType"] = adjust_type
        if intensity:
            payload["intensity"] = intensity
        return self.client.post(
            f"{self.PREFIX}/sfs/adjust/plan/accept",
            json=payload,
        )

    # ========== 9. 每公里表现 / 海拔 ==========

    @allure.step("获取训练每公里表现数据")
    def kilometer(self, log_id: str):
        """获取每公里的分段配速、心率等数据"""
        return self.client.post(
            f"{self.PREFIX}/kilometer",
            json={"logId": log_id},
        )

    @allure.step("获取训练海拔")
    def elevation(self, log_id: str):
        """获取训练的海拔变化数据"""
        return self.client.get(
            f"{self.PREFIX}/elevation", params={"logId": log_id}
        )

    # ========== 10. 训练评价 / 提升训练 ==========

    @allure.step("用户训练评价")
    def training_evaluation(self, log_id: str, score: int, reason: str = "", comment: str = ""):
        """
        提交用户对本次训练的评价

        Args:
            log_id: 训练日志ID
            score: 评分
            reason: 评分原因
            comment: 评论
        """
        payload = {"logId": log_id, "score": score}
        if reason:
            payload["reason"] = reason
        if comment:
            payload["comment"] = comment
        return self.client.post(
            f"{self.PREFIX}/training/evaluation",
            json=payload,
        )

    @allure.step("获取日计划的feedback分析过程")
    def feedback_analyze(self, log_id: str):
        """获取日计划的 feedback 模型分析详情"""
        return self.client.post(
            f"{self.PREFIX}/feedback/analyze",
            json={"logId": log_id},
        )

    @allure.step("获取推荐的提升训练")
    def improved_todo(self, log_id: str):
        """获取基于本次训练的推荐提升训练项目"""
        return self.client.post(
            f"{self.PREFIX}/improved-todo",
            json={"logId": log_id},
        )
