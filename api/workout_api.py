"""
Workout 训练模块接口

功能说明:
    封装 turing-runner 服务中跑步训练相关的 7 个接口。
    Workout 是用户实际执行跑步的核心模块，涵盖：
    - 开始/暂停/恢复/结束/中止跑步
    - 上传轨迹坐标
    - 上传分段跑数据（阈值跑、间歇跑）
    - 查询跑步状态

业务链路:
    开始跑步(start) → 上传轨迹(upload-track-points)
    → 暂停/恢复(control) → 上传分段数据(upload-segment-run)
    → 结束跑步(end)

前置依赖:
    - 需要有效的 dailyId（从 PlanAPI 获取）
    - start 接口返回 sessionId，后续所有操作都依赖该 sessionId
    - 需要 ts-user-id 请求头

关键 ID 链:
    dailyId → workout/start → sessionId → control / end / upload
"""
from __future__ import annotations

import allure

from api.base_api import BaseAPI


class WorkoutAPI(BaseAPI):
    """
    跑步训练相关接口

    方法按训练生命周期排列：
    1. 开始跑步
    2. 暂停/恢复
    3. 上传轨迹坐标
    4. 上传分段跑数据
    5. 结束跑步
    6. 中止跑步
    7. 查询跑步状态
    """

    PREFIX = "/runzo/workout"

    # ========== 1. 开始跑步 ==========

    @allure.step("开始跑步")
    def start(
        self,
        daily_id: str,
        start_time: int,
        workout_type: int = 1,
        distance_unit: str = "km",
    ):
        """
        开始一次跑步训练

        调用后返回 sessionId，该 ID 是后续所有操作（暂停、结束、上传轨迹等）的必需参数。

        Args:
            daily_id: 日计划ID（从 PlanAPI 获取）
            start_time: 开始时间戳（毫秒）
            workout_type: 跑步类型，1=室外跑，2=室内跑，默认室外跑
            distance_unit: 距离单位，km 或 mile，默认 km

        Returns:
            Response 对象，data 中包含 sessionId
        """
        return self.client.post(
            f"{self.PREFIX}/start",
            json={
                "workoutType": workout_type,
                "dailyId": daily_id,
                "startTime": start_time,
                "distanceUnit": distance_unit,
            },
        )

    # ========== 2. 暂停/恢复 ==========

    @allure.step("暂停或恢复跑步")
    def control(self, session_id: str, control_type: int, timestamp: int):
        """
        暂停或恢复跑步

        Args:
            session_id: 跑步会话ID（从 start 接口返回）
            control_type: 控制类型，1=暂停，2=恢复
            timestamp: 操作时间戳（毫秒）

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/control",
            json={
                "sessionId": session_id,
                "controlType": control_type,
                "timestamp": timestamp,
            },
        )

    @allure.step("暂停跑步")
    def pause(self, session_id: str, timestamp: int):
        """暂停跑步的便捷方法"""
        return self.control(session_id, control_type=1, timestamp=timestamp)

    @allure.step("恢复跑步")
    def resume(self, session_id: str, timestamp: int):
        """恢复跑步的便捷方法"""
        return self.control(session_id, control_type=2, timestamp=timestamp)

    # ========== 3. 上传轨迹坐标 ==========

    @allure.step("批量上传轨迹坐标")
    def upload_track_points(self, session_id: str, track_points: list[dict]):
        """
        批量上传跑步轨迹坐标

        每次最多上传 100 个轨迹点，超过需分页上传。

        Args:
            session_id: 跑步会话ID
            track_points: 轨迹点列表，每个点包含：
                - timestamp: int - 时间戳（毫秒）
                - latitude: float - 纬度
                - longitude: float - 经度
                - avgPace: str - 当前配速，如 "5'45\""
                - duration: str - 累计时长，如 "00:05:30"
                - distance: float - 累计距离（km）
                - avgHeartRate: int - 心率（可选）
                - stepRate: int - 步频（可选）
                - calories: str - 累计卡路里（可选）
                - elevation: float - 海拔高度（可选）

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/upload-track-points",
            json={
                "sessionId": session_id,
                "trackPoints": track_points,
            },
        )

    # ========== 4. 上传分段跑数据 ==========

    @allure.step("上传分段跑数据")
    def upload_segment_run(
        self,
        session_id: str,
        daily_id: str,
        running_type: str,
        segment_index: int,
        distance: float,
        duration: str,
        avg_pace: str,
        avg_heart_rate: int | None = None,
        training_phase_type: int | None = None,
    ):
        """
        上传阈值跑和间歇跑的分段数据

        Args:
            session_id: 跑步会话ID
            daily_id: 日计划ID
            running_type: 跑步类型，如 "LSD"、"Interval"、"Threshold"
            segment_index: 分段序号（从0开始）
            distance: 本段跑步距离（米）
            duration: 本段跑步时长，如 "00:05:30"
            avg_pace: 平均配速，如 "5:12"
            avg_heart_rate: 平均心率（可选）
            training_phase_type: 训练阶段，0=热身，1=实际跑，2=冷却（可选）

        Returns:
            Response 对象
        """
        payload = {
            "sessionId": session_id,
            "dailyId": daily_id,
            "runningType": running_type,
            "segmentIndex": segment_index,
            "distance": distance,
            "duration": duration,
            "avgPace": avg_pace,
        }
        if avg_heart_rate is not None:
            payload["avgHeartRate"] = avg_heart_rate
        if training_phase_type is not None:
            payload["trainingPhaseType"] = training_phase_type

        return self.client.post(
            f"{self.PREFIX}/upload-segment-run",
            json=payload,
        )

    # ========== 5. 结束跑步 ==========

    @allure.step("结束跑步")
    def end(
        self,
        session_id: str,
        end_time: int,
        duration: str,
        distance: float,
        avg_pace: str,
        avg_heart_rate: int | None = None,
        country: str = "",
        city: str = "",
    ):
        """
        结束一次跑步训练

        Args:
            session_id: 跑步会话ID
            end_time: 结束时间戳（毫秒）
            duration: 跑步总时长，如 "00:30:34"
            distance: 总距离（km）
            avg_pace: 平均配速，如 "5'12\""
            avg_heart_rate: 平均心率（可选）
            country: 国家（可选）
            city: 城市（可选）

        Returns:
            Response 对象
        """
        payload = {
            "sessionId": session_id,
            "endTime": end_time,
            "duration": duration,
            "distance": distance,
            "avgPace": avg_pace,
        }
        if avg_heart_rate is not None:
            payload["avgHeartRate"] = avg_heart_rate
        if country:
            payload["country"] = country
        if city:
            payload["city"] = city

        return self.client.post(f"{self.PREFIX}/end", json=payload)

    # ========== 6. 中止跑步 ==========

    @allure.step("中止跑步")
    def discard(self, session_id: str):
        """
        中止（丢弃）一次跑步训练

        中止后该次训练不会被记录。

        Args:
            session_id: 跑步会话ID

        Returns:
            Response 对象
        """
        return self.client.post(
            f"{self.PREFIX}/discard",
            json={"sessionId": session_id},
        )

    # ========== 7. 查询跑步状态 ==========

    @allure.step("查询跑步状态")
    def status(self):
        """
        查询当前用户的跑步状态

        可用于判断用户是否有正在进行中的跑步。

        Returns:
            Response 对象
        """
        return self.client.get(f"{self.PREFIX}/status")
