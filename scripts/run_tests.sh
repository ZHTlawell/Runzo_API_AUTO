#!/bin/bash
# ============================================================
# Runzo API 自动化测试 - 执行脚本
# ============================================================
# 功能说明:
#   封装 pytest 执行命令，支持环境/范围/并发/重试等参数。
#   可直接命令行运行，也可被 Jenkins 调用。
#
# 使用方式:
#   bash scripts/run_tests.sh                    # 默认: test环境, 全部用例
#   bash scripts/run_tests.sh test smoke         # test环境, 冒烟用例
#   bash scripts/run_tests.sh staging all 4 2    # staging环境, 全部, 4并发, 重试2次
#   bash scripts/run_tests.sh test all 1 2 testcases/test_plan/  # 指定模块
#
# 参数:
#   $1 - 环境 (test/staging)，默认 test
#   $2 - 范围 (all/smoke/p0/p1/regression)，默认 all
#   $3 - 并发数 (1/auto/N)，默认 1
#   $4 - 重试次数，默认 2
#   $5 - 测试路径，默认 testcases/
# ============================================================

set -e

# 参数
ENV=${1:-test}
SCOPE=${2:-all}
WORKERS=${3:-1}
RERUNS=${4:-2}
TEST_PATH=${5:-testcases/}
ALLURE_DIR="reports/allure-results"

echo "========================================="
echo "  Runzo API 自动化测试"
echo "  环境: ${ENV}"
echo "  范围: ${SCOPE}"
echo "  并发: ${WORKERS} workers"
echo "  重试: ${RERUNS} 次"
echo "  路径: ${TEST_PATH}"
echo "========================================="

# 清理旧报告
rm -rf ${ALLURE_DIR}
mkdir -p ${ALLURE_DIR}

# 构建 pytest 命令
CMD="python3 -m pytest ${TEST_PATH}"
CMD="${CMD} --env=${ENV}"
CMD="${CMD} --alluredir=${ALLURE_DIR}"
CMD="${CMD} --reruns=${RERUNS}"
CMD="${CMD} --reruns-delay=1"
CMD="${CMD} -v"

# 并发
if [ "${WORKERS}" != "1" ]; then
    CMD="${CMD} -n ${WORKERS}"
fi

# 范围过滤
if [ "${SCOPE}" != "all" ]; then
    CMD="${CMD} -m ${SCOPE}"
fi

echo "执行命令: ${CMD}"
echo "========================================="

# 执行测试
${CMD}
EXIT_CODE=$?

echo "========================================="
echo "  测试执行完成 (exit code: ${EXIT_CODE})"
echo "  查看报告: allure serve ${ALLURE_DIR}"
echo "  生成静态报告: allure generate ${ALLURE_DIR} -o reports/allure-report --clean"
echo "========================================="

exit ${EXIT_CODE}
