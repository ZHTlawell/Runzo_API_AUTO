"""
训练计划生成 - 端到端测试用例

功能说明:
    覆盖计划生成的完整链路测试：
    1. 设备登录 -> 获取用户身份
    2. 调用 plan/generate -> 触发异步计划生成
    3. 轮询 MongoDB -> 等待计划生成完成
    4. 查询计划列表 -> 验证计划已创建
    5. 查询周计划 -> 验证周训练数据
    6. 查询日计划 -> 获取 dailyId（供后续训练链路使用）

    同时包含参数化的异常场景测试。
    注意: 每个用户只能调用一次 plan/generate，
    因此异常测试每条用例都需要独立创建新用户。

业务链路:
    device-login -> generate -> poll MongoDB -> plan/list
    -> training-week-list -> training-daily

依赖说明:
    - auth_user / runner_client: 正向用例使用会话级用户
    - create_temp_user: 异常用例使用独立临时用户（每条用例一个新用户）
    - plan_api: 计划模块 API 对象
    - mongo_db: MongoDB 数据库连接（用于轮询计划状态）
"""
from __future__ import annotations

import allure
import pytest

from api.auth_api import AuthAPI
from api.plan_api import PlanAPI
from common.assertion import Assertion
from common.cache import cache
from common.data_loader import DataLoader
from common.http_client import HttpClient
from common.logger import log
from common.waiter import wait_for_plan_ready
from config.settings import settings

# 加载测试数据
plan_data_list = DataLoader.load("plan/generate_plan.yaml")

# 分离正向和异常用例
positive_cases = [d for d in plan_data_list if not d["case_id"].startswith("plan_gen_err")]
negative_cases = [d for d in plan_data_list if d["case_id"].startswith("plan_gen_err")]


@pytest.fixture(scope="function")
def create_temp_user(user_center_client):
    """
    函数级别的临时用户工厂

    每次调用创建一个全新的用户（通过设备登录），
    并返回一个已设置好用户身份头的 runner HttpClient。

    用于「每个用户只能调用一次 plan/generate」的场景：
    异常测试的每条用例都需要独立用户，避免重复调用 generate 接口。

    Returns:
        tuple: (user_data_dict, runner_client_with_headers)
    """
    clients_to_close = []

    def _factory():
        # 1. 设备登录创建新用户
        auth_api = AuthAPI(user_center_client)
        resp = auth_api.device_login()
        assert resp.status_code == 200, f"临时用户登录失败: {resp.text}"

        resp_data = resp.json()
        assert resp_data.get("code") == 0, f"临时用户登录业务异常: {resp_data}"

        user_data = resp_data["data"]

        # 2. 创建独立的 runner client 并设置头
        client = HttpClient(
            base_url=settings.base_url,
            timeout=settings.timeout,
        )
        client.set_headers(settings.default_headers)
        client.set_headers({
            "ts-user-id": user_data["userId"],
            "Authorization": f'Bearer {user_data["accessToken"]}',
        })

        clients_to_close.append(client)
        log.info(f"临时用户创建成功: userId={user_data['userId']}")
        return user_data, client

    yield _factory

    # Teardown: 关闭所有临时 client
    for c in clients_to_close:
        c.close()


@allure.feature("训练计划管理")
@allure.story("计划生成")
class TestPlanGenerate:
    """
    训练计划生成测试

    核心测试场景：
    - P0: 完整链路（生成 -> 轮询 -> 查询列表 -> 查询周计划 -> 查询日计划）
    - P2: 异常参数校验（每条用例独立用户）
    """

    @pytest.mark.smoke
    @pytest.mark.p0
    @allure.title("P0 冒烟: 计划生成完整链路")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_plan_generate_full_chain(self, plan_api, auth_user, mongo_db):
        """
        计划生成核心链路端到端测试

        完整流程：
        1. 调用 generate 接口触发异步计划生成
        2. 轮询 MongoDB 等待计划状态变为 3（成功）
        3. 调用 plan/list 验证计划已出现在列表中
        4. 调用 training-week-list 验证周计划数据
        5. 从周计划中提取 dailyId，调用 training-daily 验证日计划
        6. 将 planId 和 dailyId 存入全局缓存，供后续链路使用
        """
        user_id = auth_user["userId"]

        # ===== Step 1: 生成训练计划（异步） =====
        with allure.step("Step 1: 调用 plan/generate 触发计划生成"):
            plan_request = {
                "gender": 1,
                "heightValue": "175",
                "heightUnit": "cm",
                "weightValue": "70",
                "weightUnit": "kg",
                "trainingGoal": "half_marathon",
                "planCompletionWeeks": 12,
                "trainingSchedule": ["MONDAY", "WEDNESDAY", "FRIDAY", "SUNDAY"],
                "lsdSchedule": "SUNDAY",
                "age": 28,
                "intensity": "medium",
                "trainingHistory": {
                    "paceDTO": {"pace5km": "5'30\""},
                    "heartRateDTO": {"heartRate": 160},
                    "fiveKm": {"pace": "5'30\"", "heartRate": "160"},
                },
            }
            response = plan_api.generate(plan_request)
            Assertion.assert_status_code(response, 200)
            log.info(f"计划生成触发成功: {response.json()}")

        # ===== Step 2: 轮询 MongoDB 等待计划生成完成 =====
        with allure.step("Step 2: 轮询 MongoDB 等待计划生成 (最长120s)"):
            plan_doc = wait_for_plan_ready(
                mongo_db=mongo_db,
                user_id=user_id,
                timeout=120,
                interval=5,
            )
            assert plan_doc is not None, "计划文档为空"
            assert plan_doc.get("status") == 3, f"计划状态异常: {plan_doc.get('status')}"
            log.info(f"计划生成完成: planId={plan_doc.get('_id')}")

        # ===== Step 3: 查询计划列表 =====
        with allure.step("Step 3: 查询计划列表，验证计划已创建"):
            list_resp = plan_api.get_list()
            Assertion.assert_code(list_resp)

            list_data = list_resp.json()
            data = list_data.get("data")
            assert data, "计划列表 data 为空"

            # plan/list 返回格式: data 可能是对象（单个计划）或列表
            if isinstance(data, list):
                plan_obj = data[0]
            else:
                plan_obj = data

            plan_id = (
                plan_obj.get("trainingPlanId")
                or plan_obj.get("id")
                or plan_obj.get("_id")
            )
            assert plan_id, f"无法提取 planId: {plan_obj}"
            log.info(f"获取到 planId: {plan_id}")

            # 存入全局缓存
            cache.set("plan_id", plan_id)

        # ===== Step 4: 查询周计划 =====
        with allure.step("Step 4: 查询周计划训练详情"):
            week_resp = plan_api.training_week_list(plan_id)
            Assertion.assert_code(week_resp)

            week_data = week_resp.json()
            log.info("周计划查询成功")

        # ===== Step 5: 从周计划中提取 dailyId =====
        with allure.step("Step 5: 从周计划数据中提取 dailyId"):
            week_plans = week_data.get("data", [])
            daily_id = None

            # 从周计划响应中直接提取 dailyId（无需开启训练）
            for week in (week_plans if isinstance(week_plans, list) else [week_plans]):
                daily_trainings = week.get("dailyTrainings", [])
                for dt in daily_trainings:
                    did = dt.get("dailyId")
                    if did:
                        daily_id = did
                        break
                if daily_id:
                    break

            if daily_id:
                cache.set("daily_id", daily_id)
                log.info(f"获取到 dailyId: {daily_id}")

                # 查询日计划详情
                daily_resp = plan_api.training_daily(daily_id)
                Assertion.assert_code(daily_resp)
                log.info("日计划详情查询成功")
            else:
                log.warning("周计划中未找到 dailyId，跳过日计划查询")

        log.info(
            f"=== 计划生成完整链路测试通过 ===\n"
            f"    userId: {user_id}\n"
            f"    planId: {cache.get('plan_id')}\n"
            f"    dailyId: {cache.get('daily_id')}"
        )

    @pytest.mark.p2
    @pytest.mark.parametrize(
        "case_data",
        negative_cases,
        ids=[d["case_id"] for d in negative_cases],
    )
    @allure.severity(allure.severity_level.NORMAL)
    def test_plan_generate_negative(self, create_temp_user, case_data):
        """
        计划生成异常参数校验

        重要: 每个用户只能调用一次 plan/generate，
        因此每条异常用例都通过 create_temp_user 创建独立的新用户，
        确保不会因为重复调用而导致测试互相干扰。

        通过 YAML 数据文件参数化驱动。
        """
        allure.dynamic.title(case_data["title"])

        # 为本条用例创建独立的临时用户
        user_data, temp_client = create_temp_user()
        temp_plan_api = PlanAPI(temp_client)

        data = case_data["data"]
        expected = case_data["expected"]

        log.info(f"异常用例 [{case_data['case_id']}] 使用临时用户: {user_data['userId']}")

        response = temp_plan_api.generate(data)
        Assertion.assert_status_code(response, expected["status_code"])

        if "code_not" in expected:
            Assertion.assert_code_not(response, expected["code_not"])
            log.info(f"异常校验通过: {case_data['case_id']} - code={response.json().get('code')}")


@allure.feature("训练计划管理")
@allure.story("计划查询")
class TestPlanQuery:
    """
    训练计划查询相关测试

    前提条件: 需要已生成的计划（依赖 test_plan_generate_full_chain）
    通过全局缓存 cache.get("plan_id") 获取 planId
    """

    @pytest.mark.p1
    @allure.title("查询计划生成状态")
    def test_plan_status(self, plan_api, auth_user):
        """验证计划状态查询接口可正常返回"""
        response = plan_api.get_status()
        Assertion.assert_code(response)
        log.info(f"计划状态: {response.json().get('data')}")

    @pytest.mark.p1
    @allure.title("查询4周Block状态")
    def test_cycle_block_status(self, plan_api, auth_user):
        """验证4周Block状态查询"""
        plan_id = cache.get("plan_id")
        if not plan_id:
            pytest.skip("无可用的 planId，需先运行计划生成用例")

        response = plan_api.cycle_block_status(plan_id)
        Assertion.assert_code(response)
        log.info("4周Block状态查询成功")

    @pytest.mark.p1
    @allure.title("查询计划列表")
    def test_plan_list(self, plan_api, auth_user):
        """验证计划列表接口返回正确"""
        response = plan_api.get_list()
        Assertion.assert_code(response)
        plans = response.json().get("data", [])
        log.info(f"计划列表: 共 {len(plans)} 个计划")
