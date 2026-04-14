#!/bin/bash
# Allure 报告生成脚本
# 用法: bash scripts/generate_report.sh [serve|generate]

set -e

ALLURE_RESULTS="reports/allure-results"
ALLURE_REPORT="reports/allure-report"

ACTION=${1:-serve}

case ${ACTION} in
    serve)
        echo "启动 Allure 报告服务..."
        allure serve ${ALLURE_RESULTS}
        ;;
    generate)
        echo "生成 Allure 静态报告..."
        allure generate ${ALLURE_RESULTS} -o ${ALLURE_REPORT} --clean
        echo "报告已生成: ${ALLURE_REPORT}/index.html"
        ;;
    *)
        echo "用法: bash scripts/generate_report.sh [serve|generate]"
        echo "  serve    - 启动临时报告服务器"
        echo "  generate - 生成静态 HTML 报告"
        ;;
esac
