"""
训练计划模块接口

功能说明:
    封装 turing-runner 服务中与训练计划相关的所有接口（32个）。
    训练计划是整个跑步系统的核心，涵盖：
    - 计划生成（异步，需轮询MongoDB状态）
    - 4周Block周期管理
    - 周计划 / 日计划查询
    - 计划调整（交换、转移、变更）
    - 校准报告

业务链路:
    生成计划 → 轮询状态 → 查询计划列表 → 开启训练
    → 查询周计划 → 查询日计划 → 获取 dailyId（供 Workout 使用）

关键依赖:
    - 所有接口需要 ts-user-id 请求头（通过设备登录获取）
    - 生成计划后需要通过 MongoDB 轮询 runzo_training-plan.status 判断是否完成
    - status=1 生成中, status=3 成功, status=4 失败
"""
import allure

from api.base_api import BaseAPI


class PlanAPI(BaseAPI):
    """
    训练计划相关接口

    所有方法按业务流程排列：
    1. 计划生成与状态查询
    2. 计划列表与详情
    3. 周计划与日计划
    4. 计划调整与变更
    5. 4周Block周期管理
    6. 校准与训练开启
    """

    PREFIX = "/runzo/plan"

    # ========== 1. 计划生成与状态查询 ==========

    @allure.step("生成跑步训练计划（异步）")
    def generate(self, plan_data: dict):
        """
        根据用户信息生成跑步训练计划

        这是一个异步接口，调用后需要轮询 MongoDB 的 runzo_training-plan 表
        检查 status 字段来判断计划是否生成完成。

        Args:
            plan_data: GeneratePlanDTO 结构，包含:
                - gender: int - 性别
                - heightValue/heightUnit: 身高
                - weightValue/weightUnit: 体重
                - trainingGoal: str - 训练目标 (5km/10km/half_marathon/full_marathon/custom)
                - planCompletionWeeks: int - 计划周数
                - trainingSchedule: list - 训练排期 ["MONDAY","WEDNESDAY","FRIDAY"]
                - lsdSchedule: str - LSD排期 如 "SATURDAY"
                - age: int - 年龄
                - trainingHistory: dict - 训练历史（配速、心率等）
                - intensity: str - 训练强度 (high/medium/low)

        Returns:
            Response 对象
        """
        return self.client.post(f"{self.PREFIX}/generate", json=plan_data)

    @allure.step("查询计划生成状态")
    def get_status(self):
        """
        查询计划生成状态

        用于在调用 generate() 后轮询计划是否生成完成。
        也可以通过直接查询 MongoDB 来判断。

        Returns:
            Response 对象
        """
        return self.client.get(f"{self.PREFIX}/status")

    @allure.step("查询计划列表")
    def get_list(self):
        """
        获取当前用户的所有训练计划列表

        计划生成成功后调用此接口获取 planId，
        planId 是后续查询周计划、日计划、统计数据的核心依赖。

        Returns:
            Response 对象，data 中包含计划列表，每个计划含 planId
        """
        return self.client.get(f"{self.PREFIX}/list")

    # ========== 2. 周计划与日计划 ==========

    @allure.step("查询周计划训练详情列表")
    def training_week_list(self, plan_id: str):
        """
        查询指定计划的周训练详情列表

        Args:
            plan_id: 训练计划ID

        Returns:
            Response 对象，data 中包含每周的训练安排
        """
        return self.client.post(
            f"{self.PREFIX}/training-week-list",
            json={"trainingPlanId": plan_id},
        )

    @allure.step("查询用户当天的训练计划")
    def training_daily(self, daily_id: str):
        """
        查询指定日期的训练计划详情

        Args:
            daily_id: 日计划ID

        Returns:
            Response 对象，data 中包含当天训练类型、配速目标等详情
        """
        return self.client.post(
            f"{self.PREFIX}/training-daily",
            json={"dailyId": daily_id},
        )

    @allure.step("获取未训练的日计划")
    def untrained_dailies(self):
        """
        获取当前日后本周及下周未训练的日计划列表

        用于获取可用的 dailyId，供开始训练时使用。

        Returns:
            Response 对象
        """
        return self.client.get(f"{self.PREFIX}/untrained-dailies")

    # ========== 3. 计划调整与变更 ==========

    @allure.step("交换两个日计划内容")
    def daily_plan_swap(self, daily_id_1: str, daily_id_2: str):
        """
        交换两个日计划的训练内容

        Args:
            daily_id_1: 第一个日计划ID
            daily_id_2: 第二个日计划ID

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/daily-plan-swap",
            json={"dailyId1": daily_id_1, "dailyId2": daily_id_2},
        )

    @allure.step("调整训练日计划到休息日")
    def daily_plan_transfer(self, from_daily_id: str, to_daily_id: str):
        """
        将训练日的计划转移到休息日

        Args:
            from_daily_id: 源日计划ID（训练日）
            to_daily_id: 目标日计划ID（休息日）

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/daily-plan-transfer",
            json={"fromDailyId": from_daily_id, "toDailyId": to_daily_id},
        )

    @allure.step("查询训练后生成的变更计划")
    def change_plan(self, plan_id: str):
        """
        查询训练完成后系统自动生成的计划变更建议

        Args:
            plan_id: 训练计划ID

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/change-plan",
            json={"trainingPlanId": plan_id},
        )

    @allure.step("接受或拒绝变更计划")
    def change_plan_accept(self, plan_id: str, accept: bool):
        """
        用户对变更计划做出决策（接受或拒绝）

        Args:
            plan_id: 训练计划ID
            accept: True=接受变更, False=拒绝变更

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/change-plan/change",
            json={"trainingPlanId": plan_id, "accept": accept},
        )

    @allure.step("是否正在生成变更计划中")
    def exist_changing_plan(self):
        """查询当前是否有正在生成中的变更计划"""
        return self.client.get(f"{self.PREFIX}/exist-changing-plan")

    # ========== 4. 4周Block周期管理 ==========

    @allure.step("查询最新的4周block状态")
    def cycle_block_status(self, plan_id: str):
        """
        查询当前最新4周Block的状态

        Args:
            plan_id: 训练计划ID

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/cycle-block/status",
            json={"trainingPlanId": plan_id},
        )

    @allure.step("查询所有4周block状态")
    def cycle_block_status_all(self, plan_id: str):
        """查询计划所有的4周Block状态"""
        return self.client.post(
            f"{self.PREFIX}/cycle-block/status/all",
            json={"trainingPlanId": plan_id},
        )

    @allure.step("查询进行中的4周block详情")
    def cycle_block_detail_progress(self, plan_id: str):
        """查询当前进行中的4周Block详情"""
        return self.client.post(
            f"{self.PREFIX}/cycle-block/detail/progress",
            json={"trainingPlanId": plan_id},
        )

    @allure.step("查询已完成的4周block详情")
    def cycle_block_detail_finished(self, plan_id: str):
        """查询已完成的4周Block详情"""
        return self.client.post(
            f"{self.PREFIX}/cycle-block/detail/finished",
            json={"trainingPlanId": plan_id},
        )

    @allure.step("开启下一个4周block")
    def start_next_cycle(self, plan_id: str):
        """
        当前4周Block完成后，开启下一个4周Block

        Args:
            plan_id: 训练计划ID

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/start-next-cycle",
            json={"trainingPlanId": plan_id},
        )

    # ========== 5. 周Block调整 ==========

    @allure.step("查询当前周的block状态")
    def weekly_adjustment_status(self, plan_id: str):
        """查询当前周Block的调整状态"""
        return self.client.post(
            f"{self.PREFIX}/weekly/adjustment/status",
            json={"trainingPlanId": plan_id},
        )

    @allure.step("查询所有周的block状态")
    def weekly_adjustment_status_all(self, plan_id: str):
        """查询所有周Block的调整状态"""
        return self.client.post(
            f"{self.PREFIX}/weekly/adjustment/status/all",
            json={"trainingPlanId": plan_id},
        )

    @allure.step("查询周block训练总结")
    def weekly_adjustment_detail(self, plan_id: str):
        """查询指定周Block的训练总结"""
        return self.client.post(
            f"{self.PREFIX}/weekly/adjustment/detail",
            json={"trainingPlanId": plan_id},
        )

    @allure.step("接受或拒绝周block调整")
    def weekly_adjustment_change(self, plan_id: str, accept: bool):
        """接受或拒绝周Block的调整建议"""
        return self.client.post(
            f"{self.PREFIX}/weekly/adjustment/change",
            json={"trainingPlanId": plan_id, "accept": accept},
        )

    # ========== 6. 校准与训练开启 ==========

    @allure.step("校准完成开启训练")
    def start_training(self, plan_id: str):
        """
        校准完成后正式开启训练

        在计划生成成功后，需要调用此接口开启训练，
        之后才能使用 Workout 接口开始具体的跑步训练。

        Args:
            plan_id: 训练计划ID

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/start-training",
            json={"trainingPlanId": plan_id},
        )

    @allure.step("查询校准报告")
    def calibration_report(self, plan_id: str):
        """查询计划的校准报告"""
        return self.client.post(
            f"{self.PREFIX}/calibration/report",
            json={"trainingPlanId": plan_id},
        )

    @allure.step("获取训练进度校准")
    def process_calibration(self):
        """获取当前训练进度的校准信息"""
        return self.client.get(f"{self.PREFIX}/process-calibration")

    # ========== 7. 其他计划功能 ==========

    @allure.step("获取日计划对应的训练建议")
    def daily_suggestion(self, daily_id: str):
        """获取指定日计划的训练建议"""
        return self.client.post(
            f"{self.PREFIX}/daily-suggestion",
            json={"dailyId": daily_id},
        )

    @allure.step("查询专注块训练列表")
    def focus_trainings(self, plan_id: str):
        """查询训练专注块列表"""
        return self.client.post(
            f"{self.PREFIX}/focus-trainings",
            json={"trainingPlanId": plan_id},
        )

    @allure.step("查询训练专注块")
    def focus_training_block(self, plan_id: str):
        """查询当前训练专注块详情"""
        return self.client.post(
            f"{self.PREFIX}/focus-training-block",
            json={"trainingPlanId": plan_id},
        )

    @allure.step("新增休息日加练计划")
    def extra_session_generate(self, daily_id: str):
        """在休息日生成额外的训练计划"""
        return self.client.post(
            f"{self.PREFIX}/extra-session/generate",
            json={"dailyId": daily_id},
        )

    @allure.step("获取休息日加练推荐日计划")
    def extra_session(self):
        """获取推荐的休息日加练日计划"""
        return self.client.get(f"{self.PREFIX}/extra-session")

    @allure.step("查询未来7天内休息日计划")
    def next_7days_rest(self):
        """查询当前日计划未来7天内未训练的休息日计划"""
        return self.client.get(f"{self.PREFIX}/next7daysRest")
