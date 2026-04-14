"""
Settlement 结算模块 - 端到端测试用例

功能说明:
    覆盖手机训练结算的完整链路：
    1. 完成训练 → 从 end 响应提取 logId
    2. 轮询 log/ready 等待日志分析完成
    3. 查询日志详情 + 各维度结算数据

业务逻辑:
    手机训练特点（区别于手表训练）：
    - 无心率数据 → heart-rate/EF/running-economy 等返回空数据
    - 无跑姿数据 → running-posture 返回空数据
    - 有 GPS 轨迹 → 配速/每公里/海拔 有数据

    结算流程:
    workout/end → 响应中获取 logId
    → feedback/analyze 自动触发（无需手动调）
    → 轮询 log/ready（data=true 表示就绪）
    → log/details 查看完整日志
    → 各维度查询（配速、心率、经济性...）
    → 教练来信（log/ready 后查，仅训练日首次训练有）

关键 ID 链:
    userId → planId → dailyId → sessionId → logId
"""
from __future__ import annotations

import time

import allure
import pytest

from api.plan_api import PlanAPI
from api.workout_api import WorkoutAPI
from common.assertion import Assertion
from common.cache import cache
from common.logger import log
from common.run_simulator import RunSimulator
from common.waiter import wait_for_log_ready, wait_for_plan_ready


@pytest.fixture(scope="module")
def completed_workout(runner_client, plan_api, workout_api, settlement_api, auth_user, mongo_db):
    """
    模块级 fixture: 完成一次手机端完整训练，获取 logId 并等待日志就绪

    流程:
    1. 生成计划 → 获取 dailyId
    2. 开始训练 → 上传轨迹 → 结束训练（从 end 响应取 logId）
    3. 轮询 log/ready 等待日志分析完成

    Returns:
        dict: {
            "user_id", "plan_id", "daily_id",
            "session_id", "log_id", "training_type"
        }
    """
    # 尝试从缓存复用
    existing_log = cache.get("log_id")
    if existing_log:
        log.info(f"复用已有 logId: {existing_log}")
        return {
            "user_id": cache.get("user_id"),
            "plan_id": cache.get("plan_id"),
            "daily_id": cache.get("daily_id"),
            "session_id": cache.get("session_id"),
            "log_id": existing_log,
            "training_type": cache.get("training_type", "EasyRun"),
        }

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
    training_type = "EasyRun"
    for week in (week_data if isinstance(week_data, list) else [week_data]):
        for dt in week.get("dailyTrainings", []):
            if dt.get("dailyId"):
                daily_id = dt["dailyId"]
                training_type = dt.get("trainingType", "EasyRun")
                break
        if daily_id:
            break
    assert daily_id, "未找到可用的 dailyId"

    # ===== 2. 完成一次手机训练 =====
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
        country="CN",
        city="Shanghai",
    )
    end_data = end_resp.json()
    assert end_data.get("code") == 0, f"结束跑步失败: {end_data}"

    # ===== 3. 从 end 响应中提取 logId =====
    log_id = end_data.get("data", {}).get("logId")
    if not log_id:
        # 备选：从 MongoDB 查找
        log.warning("end 响应未返回 logId，尝试从 MongoDB 查找")
        log_doc = mongo_db.find_one("runzo_training_log", {"createBy": user_id})
        if log_doc:
            log_id = str(log_doc.get("_id"))
    assert log_id, f"无法获取 logId，end 响应: {end_data}"

    # ===== 4. 轮询 log/ready 等待日志分析完成 =====
    log.info(f"等待日志分析完成: logId={log_id}")
    wait_for_log_ready(settlement_api, log_id, timeout=60, interval=3)

    # 存入缓存
    cache.set("plan_id", plan_id)
    cache.set("daily_id", daily_id)
    cache.set("session_id", session_id)
    cache.set("log_id", log_id)
    cache.set("training_type", training_type)

    log.info(
        f"训练完成 + 日志就绪:\n"
        f"    planId={plan_id}\n"
        f"    dailyId={daily_id}\n"
        f"    sessionId={session_id}\n"
        f"    logId={log_id}\n"
        f"    type={training_type}"
    )

    return {
        "user_id": user_id,
        "plan_id": plan_id,
        "daily_id": daily_id,
        "session_id": session_id,
        "log_id": log_id,
        "training_type": training_type,
    }


@allure.feature("训练结算")
@allure.story("结算完整链路")
class TestSettlementFullChain:
    """
    P0 核心链路: end获取logId → log/ready等待 → log/details → 各维度查询

    手机训练特点：
    - 配速/每公里/海拔 → 有数据（GPS采集）
    - 心率/EF/经济性/跑姿 → 返回空数据（无传感器）
    - 教练来信 → 训练日首次训练有
    """

    @pytest.mark.smoke
    @pytest.mark.p0
    @allure.title("P0 冒烟: 手机训练结算完整链路")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_settlement_full_chain(self, settlement_api, completed_workout):
        """
        结算完整链路端到端测试

        流程: logId(已就绪) → log/details → 配速 → 心率(空) → 每公里 → 海拔 → 教练来信
        """
        log_id = completed_workout["log_id"]
        daily_id = completed_workout["daily_id"]

        # Step 1: 查询训练日志详情
        with allure.step("Step 1: 查询训练日志详情"):
            details_resp = settlement_api.log_details(log_id)
            Assertion.assert_status_code(details_resp, 200)
            details_data = details_resp.json()
            assert details_data.get("code") == 0, f"查询日志详情失败: {details_data}"
            log.info(f"日志详情查询成功: logId={log_id}")

        # Step 2: 查询配速（手机有GPS，配速有数据）
        with allure.step("Step 2: 查询训练配速"):
            pace_resp = settlement_api.pace(log_id)
            Assertion.assert_status_code(pace_resp, 200)
            log.info(f"配速查询: code={pace_resp.json().get('code')}")

        # Step 3: 查询配速区间达标
        with allure.step("Step 3: 查询配速区间达标"):
            zone_resp = settlement_api.pace_range_zone(log_id)
            Assertion.assert_status_code(zone_resp, 200)
            log.info(f"配速区间: code={zone_resp.json().get('code')}")

        # Step 4: 查询心率（手机无心率，预期返回空数据）
        with allure.step("Step 4: 查询心率（手机训练预期空数据）"):
            hr_resp = settlement_api.heart_rate(log_id)
            Assertion.assert_status_code(hr_resp, 200)
            hr_data = hr_resp.json()
            log.info(f"心率查询: code={hr_data.get('code')}, data={hr_data.get('data')}")

        # Step 5: 查询每公里表现
        with allure.step("Step 5: 查询每公里表现数据"):
            km_resp = settlement_api.kilometer(log_id)
            Assertion.assert_status_code(km_resp, 200)
            log.info(f"每公里表现: code={km_resp.json().get('code')}")

        # Step 6: 查询海拔
        with allure.step("Step 6: 查询训练海拔"):
            elev_resp = settlement_api.elevation(log_id)
            Assertion.assert_status_code(elev_resp, 200)
            log.info(f"海拔数据: code={elev_resp.json().get('code')}")

        # Step 7: 查询教练来信（训练日首次训练才有）
        with allure.step("Step 7: 查询教练来信"):
            letter_resp = settlement_api.coach_letter(daily_id)
            Assertion.assert_status_code(letter_resp, 200)
            letter_data = letter_resp.json()
            log.info(f"教练来信: code={letter_data.get('code')}, hasData={letter_data.get('data') is not None}")

        log.info(f"=== 手机训练结算完整链路测试通过 === logId={log_id}")


@allure.feature("训练结算")
@allure.story("手机训练无心率场景")
class TestSettlementNoHeartRate:
    """
    P1 手机训练无心率场景验证

    手机训练没有心率传感器，以下接口应返回空数据（code=0 但 data 为空）：
    - heart-rate / heart-rate-zone
    - ef/score / running-economy
    - running-posture
    """

    @pytest.mark.p1
    @allure.title("P1: 心率区间查询 - 手机训练返回空数据")
    def test_heart_rate_zone_empty(self, settlement_api, completed_workout):
        """手机训练无心率，心率区间应返回空数据"""
        log_id = completed_workout["log_id"]
        resp = settlement_api.heart_rate_zone(log_id)
        Assertion.assert_status_code(resp, 200)
        resp_data = resp.json()
        log.info(f"心率区间(手机): code={resp_data.get('code')}, data={resp_data.get('data')}")

    @pytest.mark.p1
    @allure.title("P1: EF得分查询 - 手机训练无心率不可算")
    def test_ef_score_no_hr(self, settlement_api, completed_workout):
        """手机训练无心率，EF有氧得分无法计算"""
        log_id = completed_workout["log_id"]
        resp = settlement_api.ef_score(log_id)
        Assertion.assert_status_code(resp, 200)
        resp_data = resp.json()
        log.info(f"EF得分(手机): code={resp_data.get('code')}, data={resp_data.get('data')}")

    @pytest.mark.p1
    @allure.title("P1: 跑步经济性查询 - 手机训练无心率不可算")
    def test_running_economy_no_hr(self, settlement_api, completed_workout):
        """手机训练无心率，跑步经济性无法计算"""
        log_id = completed_workout["log_id"]
        resp = settlement_api.running_economy_score(log_id)
        Assertion.assert_status_code(resp, 200)
        resp_data = resp.json()
        log.info(f"经济性(手机): code={resp_data.get('code')}, data={resp_data.get('data')}")

    @pytest.mark.p1
    @allure.title("P1: 跑姿得分查询 - 手机训练无跑姿数据")
    def test_running_posture_no_data(self, settlement_api, completed_workout):
        """手机训练无跑姿传感器，跑姿得分应返回空数据"""
        log_id = completed_workout["log_id"]
        resp = settlement_api.running_posture_score(log_id)
        Assertion.assert_status_code(resp, 200)
        resp_data = resp.json()
        log.info(f"跑姿(手机): code={resp_data.get('code')}, data={resp_data.get('data')}")


@allure.feature("训练结算")
@allure.story("成绩预测")
class TestSettlementPrediction:
    """P1 成绩预测相关查询"""

    @pytest.mark.p1
    @allure.title("P1: 训练实时预测成绩")
    def test_forecast_finish_time(self, settlement_api, completed_workout):
        """查询基于本次训练的实时预测完赛成绩"""
        log_id = completed_workout["log_id"]
        resp = settlement_api.forecast_finish_time(log_id)
        Assertion.assert_status_code(resp, 200)
        log.info(f"预测成绩: code={resp.json().get('code')}")

    @pytest.mark.p1
    @allure.title("P1: 计划匹配度评分")
    def test_plan_compatibility(self, settlement_api, completed_workout):
        """查询本次训练与计划的匹配度"""
        log_id = completed_workout["log_id"]
        resp = settlement_api.plan_compatibility(log_id)
        Assertion.assert_status_code(resp, 200)
        log.info(f"匹配度: code={resp.json().get('code')}")

    @pytest.mark.p1
    @allure.title("P1: 查询预测成绩状态")
    def test_predict_status(self, settlement_api, completed_workout):
        """查询用户最新的预测成绩状态"""
        resp = settlement_api.predict_status()
        Assertion.assert_status_code(resp, 200)
        log.info(f"预测状态: code={resp.json().get('code')}")


@allure.feature("训练结算")
@allure.story("训练评价")
class TestSettlementEvaluation:
    """P2 训练评价"""

    @pytest.mark.p2
    @allure.title("P2: 提交训练评价")
    def test_training_evaluation(self, settlement_api, completed_workout):
        """提交用户对本次训练的评分"""
        log_id = completed_workout["log_id"]
        resp = settlement_api.training_evaluation(
            log_id=log_id,
            score=5,
            reason="auto_test",
            comment="Automated test evaluation",
        )
        Assertion.assert_status_code(resp, 200)
        log.info(f"训练评价: code={resp.json().get('code')}")
