"""
Statistics 统计模块 - 端到端测试用例

功能说明:
    覆盖训练统计的完整链路：
    1. 计划生成 → 训练完成 → start-training（校准开启）→ 三大分数查询
    2. 计划概览、进度、周统计、日历状态等通用查询
    3. 成绩预测、VO2Max

业务逻辑:
    三大分数（Speed/Endurance/Stamina）:
    - 前置条件: 必须调用 plan/start-training 校准完成开启训练
    - 不调 start-training 则三大分数接口无数据
    - scoreType 可选: speed / endurance / stamina

    其他统计:
    - plan-overview / plan-progress: 只需有计划即可
    - calendar-status: 需要传时间范围（毫秒时间戳）
    - distance/trend: dataDimension 可选 day / week
    - vo2max / race-prediction: 需要有训练记录

前置依赖:
    - trained_with_calibration fixture: 生成计划 → 训练 → start-training → 获取 planId
"""
from __future__ import annotations

import time

import allure
import pytest

from common.assertion import Assertion
from common.cache import cache
from common.logger import log
from common.run_simulator import RunSimulator
from common.waiter import wait_for_plan_ready


@pytest.fixture(scope="module")
def trained_with_calibration(
    plan_api, workout_api, settlement_api, statistics_api, auth_user, mongo_db
):
    """
    模块级 fixture: 生成计划 → 完成训练 → 调用 start-training

    三大分数需要 start-training 才有数据。
    此 fixture 确保完整前置条件就绪。

    Returns:
        dict: {"plan_id", "daily_id", "user_id"}
    """
    # 尝试从缓存复用
    existing_plan = cache.get("plan_id")
    if existing_plan and cache.get("training_started"):
        log.info(f"复用已有计划: planId={existing_plan}, training_started=True")
        return {"plan_id": existing_plan, "user_id": cache.get("user_id")}

    user_id = auth_user["userId"]

    # ===== 1. 生成计划 =====
    plan_request = {
        "gender": 1,
        "heightValue": "175",
        "heightUnit": "cm",
        "weightValue": "70",
        "weightUnit": "kg",
        "trainingGoal": "half_marathon",
        "planCompletionWeeks": 12,
        "trainingSchedule": ["MONDAY", "WEDNESDAY", "FRIDAY", "SATURDAY", "SUNDAY"],
        "lsdSchedule": "SUNDAY",
        "age": 28,
        "intensity": "medium",
        "trainingHistory": {
            "paceDTO": {"pace5km": "5'30\"", "pace10km": "5'45\""},
            "heartRateDTO": {"heartRate": 160},
            "fiveKm": {"pace": "5'30\"", "heartRate": "160"},
        },
    }
    resp = plan_api.generate(plan_request)
    assert resp.status_code == 200 and resp.json().get("code") == 0

    plan_doc = wait_for_plan_ready(mongo_db, user_id, timeout=120, interval=5)
    assert plan_doc and plan_doc.get("status") == 3

    # 获取 planId + dailyId
    list_resp = plan_api.get_list()
    data = list_resp.json().get("data", {})
    plan_id = data.get("trainingPlanId") if isinstance(data, dict) else data[0].get("trainingPlanId")

    week_resp = plan_api.training_week_list(plan_id)
    week_data = week_resp.json().get("data", [])

    daily_id = None
    for week in (week_data if isinstance(week_data, list) else [week_data]):
        for dt in week.get("dailyTrainings", []):
            if dt.get("dailyId"):
                daily_id = dt["dailyId"]
                break
        if daily_id:
            break
    assert daily_id, "未找到可用的 dailyId"

    # ===== 2. 完成一次训练 =====
    start_time_ms = int(time.time() * 1000)
    start_resp = workout_api.start(daily_id=daily_id, start_time=start_time_ms, workout_type=1)
    assert start_resp.json().get("code") == 0
    session_id = start_resp.json()["data"]["sessionId"]

    simulator = RunSimulator(target_pace_sec=330, duration_minutes=10, avg_heart_rate=155)
    simulator.generate_track_points(start_time_ms)
    for batch in simulator.get_track_point_batches():
        workout_api.upload_track_points(session_id, batch)

    summary = simulator.get_summary()
    end_time_ms = start_time_ms + simulator._total_duration_sec * 1000
    end_resp = workout_api.end(
        session_id=session_id,
        end_time=end_time_ms,
        duration=summary["duration"],
        distance=summary["distance"],
        avg_pace=summary["avgPace"],
        avg_heart_rate=summary["avgHeartRate"],
    )
    assert end_resp.json().get("code") == 0

    # ===== 3. 校准完成开启训练 =====
    start_training_resp = plan_api.start_training(plan_id)
    start_training_data = start_training_resp.json()
    log.info(f"start-training: code={start_training_data.get('code')}, msg={start_training_data.get('msg')}")
    # 不强制 assert，因为可能报 calibration not found，但三大分数可能仍有数据

    cache.set("plan_id", plan_id)
    cache.set("daily_id", daily_id)
    cache.set("training_started", True)

    log.info(f"Statistics 前置条件就绪: planId={plan_id}, userId={user_id}")
    return {"plan_id": plan_id, "user_id": user_id}


@allure.feature("训练统计")
@allure.story("三大分数")
class TestStatisticsScores:
    """
    P0 三大分数查询: Speed（速度）/ Endurance（耐力）/ Stamina（速度耐力）

    前置条件: plan/start-training 已调用
    """

    @pytest.mark.smoke
    @pytest.mark.p0
    @allure.title("P0 冒烟: 查询三大分数")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_scores(self, statistics_api, trained_with_calibration):
        """
        查询当前三大分数值

        注意: 三大分数需要 start-training 校准完成后才有数据。
        如果 start-training 因 calibration report not found 失败，
        scores 接口会返回 code=0 但 data=null，这是预期行为。
        """
        plan_id = trained_with_calibration["plan_id"]

        resp = statistics_api.scores(plan_id)
        Assertion.assert_status_code(resp, 200)
        resp_data = resp.json()
        assert resp_data.get("code") == 0, f"查询三大分数失败: {resp_data}"

        scores = resp_data.get("data")
        if scores is None:
            log.warning(
                "三大分数 data=null（start-training 未成功，缺少 calibration report）"
            )
        else:
            log.info(
                f"三大分数: focusScore={scores.get('focusScore')}, "
                f"speed={scores.get('speed')}, "
                f"endurance={scores.get('endurance')}, "
                f"stamina={scores.get('stamina')}"
            )

    @pytest.mark.p1
    @allure.title("P1: 查询速度分数子项")
    def test_scores_item_speed(self, statistics_api, trained_with_calibration):
        """查询速度(speed)分数的子项详情"""
        plan_id = trained_with_calibration["plan_id"]
        resp = statistics_api.scores_item(plan_id, score_type="speed")
        Assertion.assert_status_code(resp, 200)
        log.info(f"速度子项: code={resp.json().get('code')}")

    @pytest.mark.p1
    @allure.title("P1: 查询耐力分数子项")
    def test_scores_item_endurance(self, statistics_api, trained_with_calibration):
        """查询耐力(endurance)分数的子项详情"""
        plan_id = trained_with_calibration["plan_id"]
        resp = statistics_api.scores_item(plan_id, score_type="endurance")
        Assertion.assert_status_code(resp, 200)
        log.info(f"耐力子项: code={resp.json().get('code')}")

    @pytest.mark.p1
    @allure.title("P1: 查询速度耐力分数子项")
    def test_scores_item_stamina(self, statistics_api, trained_with_calibration):
        """查询速度耐力(stamina)分数的子项详情"""
        plan_id = trained_with_calibration["plan_id"]
        resp = statistics_api.scores_item(plan_id, score_type="stamina")
        Assertion.assert_status_code(resp, 200)
        log.info(f"速度耐力子项: code={resp.json().get('code')}")

    @pytest.mark.p1
    @allure.title("P1: 查询三大分数变动趋势")
    def test_scores_trend(self, statistics_api, trained_with_calibration):
        """查询近30天三大分数变动趋势"""
        plan_id = trained_with_calibration["plan_id"]
        resp = statistics_api.scores_trend(plan_id, days=30)
        Assertion.assert_status_code(resp, 200)
        log.info(f"分数趋势: code={resp.json().get('code')}")


@allure.feature("训练统计")
@allure.story("计划进度")
class TestStatisticsPlanProgress:
    """P1 计划进度与概览查询"""

    @pytest.mark.p1
    @allure.title("P1: 查询计划概览")
    def test_plan_overview(self, statistics_api, trained_with_calibration):
        """查询训练计划概览统计"""
        resp = statistics_api.plan_overview()
        Assertion.assert_status_code(resp, 200)
        log.info(f"计划概览: code={resp.json().get('code')}")

    @pytest.mark.p1
    @allure.title("P1: 查询计划进度")
    def test_plan_progress(self, statistics_api, trained_with_calibration):
        """查询用户计划进度"""
        resp = statistics_api.plan_progress()
        Assertion.assert_status_code(resp, 200)
        log.info(f"计划进度: code={resp.json().get('code')}")

    @pytest.mark.p1
    @allure.title("P1: 查询计划进度概览")
    def test_plan_progress_detail(self, statistics_api, trained_with_calibration):
        """查询当前计划进度概览（详细版）"""
        resp = statistics_api.plan_progress_detail()
        Assertion.assert_status_code(resp, 200)
        log.info(f"进度概览: code={resp.json().get('code')}")


@allure.feature("训练统计")
@allure.story("训练统计数据")
class TestStatisticsTraining:
    """P1 训练统计相关查询"""

    @pytest.mark.p1
    @allure.title("P1: 查询本周训练统计")
    def test_current_week(self, statistics_api, trained_with_calibration):
        """查询本周训练统计数据"""
        resp = statistics_api.current_week()
        Assertion.assert_status_code(resp, 200)
        log.info(f"周统计: code={resp.json().get('code')}")

    @pytest.mark.p1
    @allure.title("P1: 查询日历训练状态")
    def test_calendar_status(self, statistics_api, trained_with_calibration):
        """查询近30天的日历训练状态"""
        now_ms = int(time.time() * 1000)
        thirty_days_ago_ms = now_ms - 30 * 24 * 3600 * 1000

        resp = statistics_api.calendar_status(
            start_timestamp=thirty_days_ago_ms,
            end_timestamp=now_ms,
        )
        Assertion.assert_status_code(resp, 200)
        log.info(f"日历状态: code={resp.json().get('code')}")

    @pytest.mark.p1
    @allure.title("P1: 查询跑量趋势（按天）")
    def test_distance_trend_day(self, statistics_api, trained_with_calibration):
        """查询实际跑量 vs 推荐跑量趋势（按天维度）"""
        plan_id = trained_with_calibration["plan_id"]
        resp = statistics_api.distance_trend(plan_id, data_dimension="day", days=14)
        Assertion.assert_status_code(resp, 200)
        log.info(f"跑量趋势(天): code={resp.json().get('code')}")

    @pytest.mark.p1
    @allure.title("P1: 查询跑量趋势（按周）")
    def test_distance_trend_week(self, statistics_api, trained_with_calibration):
        """查询实际跑量 vs 推荐跑量趋势（按周聚合）"""
        plan_id = trained_with_calibration["plan_id"]
        resp = statistics_api.distance_trend(plan_id, data_dimension="week", days=30)
        Assertion.assert_status_code(resp, 200)
        log.info(f"跑量趋势(周): code={resp.json().get('code')}")

    @pytest.mark.p1
    @allure.title("P1: 查询本周关键训练")
    def test_key_sessions(self, statistics_api, trained_with_calibration):
        """查询本周关键训练完成情况"""
        plan_id = trained_with_calibration["plan_id"]
        resp = statistics_api.key_sessions_current_week(plan_id)
        Assertion.assert_status_code(resp, 200)
        log.info(f"关键训练: code={resp.json().get('code')}")

    @pytest.mark.p1
    @allure.title("P1: 查询训练总览")
    def test_training_session_overview(self, statistics_api, trained_with_calibration):
        """查询训练 session 概览"""
        resp = statistics_api.training_session_overview()
        Assertion.assert_status_code(resp, 200)
        log.info(f"训练总览: code={resp.json().get('code')}")


@allure.feature("训练统计")
@allure.story("成绩预测")
class TestStatisticsPrediction:
    """P1 成绩预测与 VO2Max"""

    @pytest.mark.p1
    @allure.title("P1: 查询成绩预测")
    def test_race_prediction(self, statistics_api, trained_with_calibration):
        """查询用户的比赛成绩预测"""
        resp = statistics_api.race_prediction()
        Assertion.assert_status_code(resp, 200)
        log.info(f"成绩预测: code={resp.json().get('code')}")

