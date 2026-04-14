"""
测试数据加载器
支持 YAML、JSON 格式的测试数据加载，配合 pytest.mark.parametrize 使用
"""
import json
from pathlib import Path

import yaml

from common.logger import log

# 测试数据根目录
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "testdata"


class DataLoader:
    """测试数据加载工具"""

    @staticmethod
    def load_yaml(file_path: str) -> list[dict]:
        """
        加载 YAML 测试数据

        Args:
            file_path: 相对于 testdata 目录的路径，如 "user/register.yaml"

        Returns:
            测试数据列表
        """
        full_path = DATA_DIR / file_path
        if not full_path.exists():
            log.error(f"测试数据文件不存在: {full_path}")
            raise FileNotFoundError(f"测试数据文件不存在: {full_path}")

        with open(full_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        log.info(f"加载测试数据: {file_path}，共 {len(data)} 条")
        return data

    @staticmethod
    def load_json(file_path: str) -> list[dict]:
        """
        加载 JSON 测试数据

        Args:
            file_path: 相对于 testdata 目录的路径，如 "user/register.json"

        Returns:
            测试数据列表
        """
        full_path = DATA_DIR / file_path
        if not full_path.exists():
            log.error(f"测试数据文件不存在: {full_path}")
            raise FileNotFoundError(f"测试数据文件不存在: {full_path}")

        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        log.info(f"加载测试数据: {file_path}，共 {len(data)} 条")
        return data

    @staticmethod
    def load(file_path: str) -> list[dict]:
        """
        自动识别格式并加载测试数据

        Args:
            file_path: 相对于 testdata 目录的路径

        Returns:
            测试数据列表
        """
        if file_path.endswith((".yaml", ".yml")):
            return DataLoader.load_yaml(file_path)
        elif file_path.endswith(".json"):
            return DataLoader.load_json(file_path)
        else:
            raise ValueError(f"不支持的数据文件格式: {file_path}")

    @staticmethod
    def parametrize_data(file_path: str) -> list[tuple]:
        """
        加载数据并转换为 pytest.mark.parametrize 需要的格式

        Args:
            file_path: 数据文件路径

        Returns:
            [(case_id, data_dict), ...] 格式的列表
        """
        data_list = DataLoader.load(file_path)
        result = []
        for item in data_list:
            case_id = item.get("case_id", "unknown")
            result.append((case_id, item))
        return result

    @staticmethod
    def parametrize_ids(file_path: str) -> list[str]:
        """
        获取用例 ID 列表，用于 parametrize 的 ids 参数

        Args:
            file_path: 数据文件路径

        Returns:
            case_id 列表
        """
        data_list = DataLoader.load(file_path)
        return [item.get("case_id", f"case_{i}") for i, item in enumerate(data_list)]
