#!/bin/bash
# 测试执行脚本
# 用法: bash scripts/run_tests.sh [env] [scope] [workers]
# 示例: bash scripts/run_tests.sh test smoke 4

set -e

# 参数
ENV=${1:-test}
SCOPE=${2:-all}
WORKERS=${3:-4}
RERUNS=${4:-2}
ALLURE_DIR="reports/allure-results"

echo "========================================="
echo "  Runzo API 自动化测试"
echo "  环境: ${ENV}"
echo "  范围: ${SCOPE}"
echo "  并发: ${WORKERS} workers"
echo "  重试: ${RERUNS} 次"
echo "========================================="

# 清理旧报告
rm -rf ${ALLURE_DIR}/*

# 构建 pytest 命令
CMD="python3 -m pytest testcases/"
CMD="${CMD} --env=${ENV}"
CMD="${CMD} -n ${WORKERS}"
CMD="${CMD} --reruns=${RERUNS}"
CMD="${CMD} --reruns-delay=1"
CMD="${CMD} --alluredir=${ALLURE_DIR}"
CMD="${CMD} -v"

if [ "${SCOPE}" != "all" ]; then
    CMD="${CMD} -m ${SCOPE}"
fi

echo "执行命令: ${CMD}"
echo "========================================="

# 执行测试
${CMD}

echo "========================================="
echo "  测试执行完成"
echo "  查看报告: allure serve ${ALLURE_DIR}"
echo "========================================="
