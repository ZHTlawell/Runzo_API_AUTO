# Runzo API 自动化测试框架

基于 **Requests + Pytest + Allure** 的企业级 API 自动化测试框架。

## 技术栈

- Python 3.10+
- Requests - HTTP 请求
- Pytest - 测试框架
- Allure - 测试报告
- MongoDB - 数据库校验
- Locust - 性能测试
- Jenkins - CI/CD

## 项目结构

```
Runzo_API_AUTO/
├── config/          # 多环境配置
├── common/          # 公共工具（HTTP封装、日志、断言、数据库、缓存）
├── api/             # API层（接口统一管理）
├── testcases/       # 测试用例（按模块组织）
├── testdata/        # 测试数据（YAML参数化）
├── fixtures/        # Pytest Fixtures
├── performance/     # Locust性能测试
├── reports/         # Allure测试报告
├── logs/            # 运行日志
├── scripts/         # 辅助脚本
└── Jenkinsfile      # CI/CD Pipeline
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

编辑 `config/env_config.yaml`，填入实际的环境地址和数据库信息。

### 3. 运行测试

```bash
# 运行全部用例（默认test环境）
pytest --env=test

# 运行冒烟测试
pytest -m smoke --env=dev

# 并发执行 + 失败重试 + 生成报告
pytest -n 4 --reruns=2 --alluredir=reports/allure-results

# 使用脚本运行
bash scripts/run_tests.sh test smoke 4
```

### 4. 查看报告

```bash
allure serve reports/allure-results
```

### 5. 性能测试

```bash
# Web UI 模式
locust -f performance/locustfile.py --host=http://test-api.example.com

# 命令行模式
locust -f performance/locustfile.py --host=http://test-api.example.com \
    --users=100 --spawn-rate=10 --run-time=5m --headless
```

## 框架特性

| 特性 | 实现方式 |
|------|----------|
| HTTP请求封装 | `common/http_client.py` - 基于 requests.Session |
| API统一管理 | `api/` - 分模块管理接口 |
| 多环境配置 | `config/env_config.yaml` + `--env` 参数 |
| 数据参数化 | YAML 文件 + `@pytest.mark.parametrize` |
| 统一断言 | `common/assertion.py` - 状态码/JSONPath/Schema/DB |
| 日志管理 | `common/logger.py` - loguru 按天轮转 |
| 接口关联 | `common/cache.py` 全局缓存 + Fixtures 依赖链 |
| 数据库校验 | `common/db_handler.py` - MongoDB CRUD |
| 测试报告 | Allure - 自动附加请求/响应详情 |
| 失败重试 | pytest-rerunfailures |
| 并发测试 | pytest-xdist |
| 性能测试 | Locust |
| CI/CD | Jenkinsfile Pipeline |
| 测试通知 | 钉钉/企业微信机器人 |

## 用例管理

- `@pytest.mark.smoke` - 冒烟测试
- `@pytest.mark.regression` - 回归测试
- `@pytest.mark.p0` ~ `@pytest.mark.p3` - 优先级标记
- Allure: `@allure.feature` / `@allure.story` / `@allure.title` - 报告分层
