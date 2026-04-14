"""
跑步数据模拟器

功能说明:
    生成模拟真实跑步场景的轨迹点数据和汇总数据，用于 Workout 接口测试。
    模拟逻辑：
    - 以起点经纬度为基准，按固定方向逐步移动
    - 每个点间隔固定秒数（默认5秒），模拟GPS上报频率
    - 配速、心率在合理范围内随机波动
    - 距离按配速和时间累加计算
    - 支持配置训练时长、目标配速、心率区间

使用示例:
    simulator = RunSimulator(
        start_lat=31.2304,    # 上海
        start_lng=121.4737,
        target_pace_sec=330,  # 目标配速 5'30"/km
        duration_minutes=30,  # 跑30分钟
    )
    points = simulator.generate_track_points(start_time_ms)
    summary = simulator.get_summary()
"""
from __future__ import annotations

import math
import random


class RunSimulator:
    """
    跑步数据模拟器

    根据配置参数生成一组真实感的轨迹点（TrackPointDTO）和训练汇总数据（EndWorkoutDTO）。

    属性:
        points: 生成的轨迹点列表
        summary: 训练汇总（总距离、总时长、平均配速、平均心率）
    """

    def __init__(
        self,
        start_lat: float = 31.2304,
        start_lng: float = 121.4737,
        target_pace_sec: int = 330,
        duration_minutes: int = 30,
        avg_heart_rate: int = 155,
        interval_sec: int = 5,
    ):
        """
        初始化模拟器

        Args:
            start_lat: 起点纬度（默认上海）
            start_lng: 起点经度
            target_pace_sec: 目标配速，单位秒/公里（330 = 5'30"/km）
            duration_minutes: 跑步时长（分钟）
            avg_heart_rate: 平均心率
            interval_sec: 轨迹点上报间隔（秒），默认5秒
        """
        self.start_lat = start_lat
        self.start_lng = start_lng
        self.target_pace_sec = target_pace_sec
        self.duration_minutes = duration_minutes
        self.avg_heart_rate = avg_heart_rate
        self.interval_sec = interval_sec

        self._points: list[dict] = []
        self._total_distance: float = 0.0
        self._total_duration_sec: int = 0
        self._heart_rates: list[int] = []

    def generate_track_points(self, start_time_ms: int) -> list[dict]:
        """
        生成轨迹点列表

        Args:
            start_time_ms: 跑步开始时间戳（毫秒）

        Returns:
            轨迹点列表，每个点为 TrackPointDTO 格式的字典
        """
        total_seconds = self.duration_minutes * 60
        num_points = total_seconds // self.interval_sec

        # 每个 interval 跑的距离（km）
        speed_km_per_sec = 1.0 / self.target_pace_sec
        distance_per_interval = speed_km_per_sec * self.interval_sec

        # 移动方向（模拟沿着一条路跑，略有弯曲）
        # 1度纬度 ≈ 111km, 1度经度 ≈ 111km * cos(lat)
        lat = self.start_lat
        lng = self.start_lng
        bearing = random.uniform(0, 360)  # 随机初始方向

        cumulative_distance = 0.0
        self._points = []
        self._heart_rates = []

        for i in range(num_points):
            elapsed_sec = (i + 1) * self.interval_sec
            timestamp = start_time_ms + elapsed_sec * 1000

            # 配速在目标值 ±15% 范围内波动
            pace_variation = random.uniform(0.85, 1.15)
            current_pace_sec = int(self.target_pace_sec * pace_variation)
            actual_distance = (1.0 / current_pace_sec) * self.interval_sec

            cumulative_distance += actual_distance

            # 心率在平均值 ±10 范围内波动
            hr = self.avg_heart_rate + random.randint(-10, 10)
            self._heart_rates.append(hr)

            # 移动经纬度（方向轻微偏转模拟自然跑步路线）
            bearing += random.uniform(-5, 5)
            bearing_rad = math.radians(bearing)
            # 将距离(km)转换为经纬度偏移
            delta_lat = (actual_distance / 111.0) * math.cos(bearing_rad)
            delta_lng = (actual_distance / (111.0 * math.cos(math.radians(lat)))) * math.sin(bearing_rad)
            lat += delta_lat
            lng += delta_lng

            # 步频在 170-185 之间
            step_rate = random.randint(170, 185)

            # 格式化配速为 "M'SS\"" 格式
            pace_min = current_pace_sec // 60
            pace_sec_part = current_pace_sec % 60
            pace_str = f"{pace_min}'{pace_sec_part:02d}\""

            # 格式化时长为 "HH:MM:SS"
            h = elapsed_sec // 3600
            m = (elapsed_sec % 3600) // 60
            s = elapsed_sec % 60
            duration_str = f"{h:02d}:{m:02d}:{s:02d}"

            point = {
                "timestamp": timestamp,
                "latitude": round(lat, 6),
                "longitude": round(lng, 6),
                "avgPace": pace_str,
                "duration": duration_str,
                "distance": round(cumulative_distance, 3),
                "avgHeartRate": hr,
                "stepRate": step_rate,
                "elevation": round(random.uniform(3.0, 15.0), 1),
            }
            self._points.append(point)

        self._total_distance = cumulative_distance
        self._total_duration_sec = num_points * self.interval_sec

        return self._points

    def get_track_point_batches(self, batch_size: int = 100) -> list[list[dict]]:
        """
        将轨迹点按批次拆分（API 限制每次最多100个点）

        Args:
            batch_size: 每批最大数量，默认100

        Returns:
            批次列表 [[point1, point2, ...], [point101, ...], ...]
        """
        return [
            self._points[i:i + batch_size]
            for i in range(0, len(self._points), batch_size)
        ]

    def get_summary(self) -> dict:
        """
        获取训练汇总数据（用于 workout/end 接口）

        Returns:
            dict 包含:
                - distance: 总距离（km）
                - duration: 总时长字符串 "HH:MM:SS"
                - avgPace: 平均配速字符串 "M'SS\""
                - avgHeartRate: 平均心率
        """
        h = self._total_duration_sec // 3600
        m = (self._total_duration_sec % 3600) // 60
        s = self._total_duration_sec % 60
        duration_str = f"{h:02d}:{m:02d}:{s:02d}"

        # 计算平均配速
        if self._total_distance > 0:
            avg_pace_sec = int(self._total_duration_sec / self._total_distance)
        else:
            avg_pace_sec = self.target_pace_sec
        pace_min = avg_pace_sec // 60
        pace_sec_part = avg_pace_sec % 60
        avg_pace_str = f"{pace_min}'{pace_sec_part:02d}\""

        avg_hr = (
            sum(self._heart_rates) // len(self._heart_rates)
            if self._heart_rates
            else self.avg_heart_rate
        )

        return {
            "distance": round(self._total_distance, 2),
            "duration": duration_str,
            "avgPace": avg_pace_str,
            "avgHeartRate": avg_hr,
        }

    def get_segment_data(
        self,
        daily_id: str,
        session_id: str,
        running_type: str = "Threshold",
    ) -> list[dict]:
        """
        生成分段跑数据（用于 upload-segment-run 接口）

        将整段训练拆为 3 个阶段：热身(20%) → 实际跑(60%) → 冷却(20%)

        Args:
            daily_id: 日计划ID
            session_id: 跑步会话ID
            running_type: 跑步类型，如 "Threshold"、"Interval"

        Returns:
            分段数据列表
        """
        total_pts = len(self._points)
        if total_pts == 0:
            return []

        # 按 20/60/20 比例拆分
        warmup_end = int(total_pts * 0.2)
        actual_end = int(total_pts * 0.8)

        segments = []
        phases = [
            (0, warmup_end, 0, "热身"),
            (warmup_end, actual_end, 1, "实际跑"),
            (actual_end, total_pts, 2, "冷却"),
        ]

        for idx, (start_idx, end_idx, phase_type, _) in enumerate(phases):
            phase_points = self._points[start_idx:end_idx]
            if not phase_points:
                continue

            dist_start = self._points[start_idx - 1]["distance"] if start_idx > 0 else 0
            dist_end = phase_points[-1]["distance"]
            seg_distance = (dist_end - dist_start) * 1000  # 转为米

            seg_duration_sec = len(phase_points) * self.interval_sec
            h = seg_duration_sec // 3600
            m = (seg_duration_sec % 3600) // 60
            s = seg_duration_sec % 60

            avg_hr = sum(p["avgHeartRate"] for p in phase_points) // len(phase_points)
            avg_pace_sec = int(seg_duration_sec / (seg_distance / 1000)) if seg_distance > 0 else self.target_pace_sec
            pace_min = avg_pace_sec // 60
            pace_sec = avg_pace_sec % 60

            segments.append({
                "sessionId": session_id,
                "dailyId": daily_id,
                "runningType": running_type,
                "segmentIndex": idx,
                "distance": round(seg_distance, 1),
                "duration": f"{h:02d}:{m:02d}:{s:02d}",
                "avgPace": f"{pace_min}:{pace_sec:02d}",
                "avgHeartRate": avg_hr,
                "trainingPhaseType": phase_type,
            })

        return segments
