"""
全局配置加载器（base + env 合并模式）

功能说明:
    1. 加载 config/base.yaml 作为基础配置
    2. 加载 config/{env}.yaml 作为环境差异配置
    3. 将环境配置深度合并到基础配置上（环境覆盖 base）
    4. 通过 --env 命令行参数或 ENV 环境变量切换环境

合并规则:
    - 简单值（字符串/数字/布尔）: 环境值直接覆盖 base 值
    - 字典类型: 递归深度合并（环境的 key 覆盖 base 同名 key，其余保留）
    - 列表类型: 环境值直接替换（不做元素级合并）

示例:
    base.yaml:                    test.yaml:
      timeout: 30                   log_level: "DEBUG"
      mongodb:                      mongodb:
        db_name: "echo"               uri: "mongodb://..."
      default_headers:
        ts-country: "CN"

    合并结果:
      timeout: 30                 ← base（test 没有覆盖）
      log_level: "DEBUG"          ← test 覆盖
      mongodb:
        db_name: "echo"           ← base 保留
        uri: "mongodb://..."      ← test 新增
      default_headers:
        ts-country: "CN"          ← base 保留

使用方式:
    from config.settings import settings
    settings.load("test")
    print(settings.base_url)
    print(settings.mongodb)  # 已经是合并后的结果
"""
import copy
import os
from pathlib import Path
from typing import Optional

import yaml


# 项目根目录（Runzo_API_AUTO/）
BASE_DIR = Path(__file__).resolve().parent.parent

# 默认环境
DEFAULT_ENV = "test"

# 支持的环境列表
VALID_ENVS = ["test", "staging"]


def deep_merge(base: dict, override: dict) -> dict:
    """
    递归深度合并两个字典

    将 override 中的内容合并到 base 上：
    - 字典类型: 递归合并（不丢失 base 中 override 没有的 key）
    - 其他类型: override 直接覆盖 base

    Args:
        base: 基础配置字典
        override: 覆盖配置字典

    Returns:
        合并后的新字典（不修改原字典）
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class Settings:
    """
    全局配置管理器（单例模式，base + env 合并机制）

    加载流程:
        1. 读取 config/base.yaml → 基础配置
        2. 读取 config/{env}.yaml → 环境差异配置
        3. deep_merge(base, env) → 最终配置

    提供的属性:
        - base_url: turing-runner 服务地址
        - user_center_url: turing-user-center 用户认证服务地址
        - mongodb: MongoDB 连接配置（已合并，包含 uri + db_name）
        - default_headers: 公共请求头（ts-time-zone-id, ts-country 等）
        - timeout: 请求超时时间
        - log_level: 日志级别
        - auth: 认证相关配置（app_name 等）
    """

    _instance = None
    _config: dict = {}
    _env: str = ""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, env: Optional[str] = None):
        """
        加载并合并配置

        Args:
            env: 环境名称（test/staging），为空时从环境变量 ENV 读取，默认 test

        Returns:
            self（支持链式调用）

        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 环境名不合法
        """
        self._env = env or os.getenv("ENV", DEFAULT_ENV)
        config_dir = BASE_DIR / "config"

        # 1. 加载 base.yaml
        base_path = config_dir / "base.yaml"
        if not base_path.exists():
            raise FileNotFoundError(f"基础配置文件不存在: {base_path}")

        with open(base_path, "r", encoding="utf-8") as f:
            base_config = yaml.safe_load(f) or {}

        # 2. 加载 {env}.yaml
        env_path = config_dir / f"{self._env}.yaml"
        if not env_path.exists():
            raise FileNotFoundError(
                f"环境配置文件不存在: {env_path}，"
                f"可用环境: {[p.stem for p in config_dir.glob('*.yaml') if p.stem != 'base']}"
            )

        with open(env_path, "r", encoding="utf-8") as f:
            env_config = yaml.safe_load(f) or {}

        # 3. 深度合并: base + env
        self._config = deep_merge(base_config, env_config)
        return self

    @property
    def env(self) -> str:
        """当前环境名称"""
        return self._env

    @property
    def base_url(self) -> str:
        """turing-runner 服务地址（跑步核心业务）"""
        return self._config.get("base_url", "")

    @property
    def user_center_url(self) -> str:
        """turing-user-center 服务地址（用户认证）"""
        return self._config.get("user_center_url", "")

    @property
    def timeout(self) -> int:
        """HTTP 请求超时时间（秒）"""
        return self._config.get("timeout", 30)

    @property
    def mongodb(self) -> dict:
        """MongoDB 连接配置（已合并 base + env，包含 uri 和 db_name）"""
        return self._config.get("mongodb", {})

    @property
    def default_headers(self) -> dict:
        """公共请求头默认值（ts-time-zone-id, ts-country 等）"""
        return self._config.get("default_headers", {})

    @property
    def auth(self) -> dict:
        """认证相关配置（app_name 等）"""
        return self._config.get("auth", {})

    @property
    def log_level(self) -> str:
        """日志级别（DEBUG/INFO/WARNING/ERROR）"""
        return self._config.get("log_level", "INFO")

    def get(self, key: str, default=None):
        """获取任意配置项"""
        return self._config.get(key, default)

    def all(self) -> dict:
        """获取完整的合并后配置（调试用）"""
        return self._config.copy()


# 全局配置实例
settings = Settings()
