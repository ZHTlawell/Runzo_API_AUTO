/**
 * Runzo API 自动化测试 - Jenkins Pipeline
 *
 * 功能说明:
 *   1. 拉取代码 → 安装依赖 → 执行测试 → 生成 Allure 报告 → 飞书通知
 *   2. 支持参数化: 环境选择、测试范围、并发数、重试次数
 *   3. 失败自动通知到飞书群（含失败用例列表和报告链接）
 *
 * 使用方式:
 *   Jenkins Job → Build with Parameters → 选择环境和范围 → 构建
 *
 * 前置要求:
 *   - Jenkins 已安装 Allure Plugin
 *   - Jenkins 节点已安装 Python 3.9+ 和 pip
 *   - Jenkins 凭据中配置 FEISHU_WEBHOOK（飞书机器人 Webhook URL）
 */
pipeline {
    agent any

    parameters {
        choice(
            name: 'ENV',
            choices: ['test', 'staging'],
            description: '选择测试环境'
        )
        choice(
            name: 'TEST_SCOPE',
            choices: ['all', 'smoke', 'p0', 'p1', 'regression'],
            description: '测试范围（all=全部, smoke=冒烟, p0=最高优先级）'
        )
        string(
            name: 'TEST_PATH',
            defaultValue: 'testcases/',
            description: '测试路径（可指定模块: testcases/test_plan/）'
        )
        string(
            name: 'PARALLEL_WORKERS',
            defaultValue: '1',
            description: '并发 Worker 数量（1=串行，auto=自动检测CPU核数）'
        )
        string(
            name: 'RERUNS',
            defaultValue: '2',
            description: '失败重试次数'
        )
    }

    environment {
        ALLURE_RESULTS = 'reports/allure-results'
        // 飞书 Webhook（推荐通过 Jenkins Credentials 管理，ID: feishu-webhook）
        // 如已配置凭据，取消下行注释并删除直接赋值行：
        // FEISHU_WEBHOOK = credentials('feishu-webhook')
        FEISHU_WEBHOOK = 'https://open.feishu.cn/open-apis/bot/v2/hook/060e25e7-7635-4a83-9050-c291fb20c386'
    }

    stages {
        stage('环境准备') {
            steps {
                echo "=== Runzo API 自动化测试 ==="
                echo "环境: ${params.ENV}"
                echo "范围: ${params.TEST_SCOPE}"
                echo "路径: ${params.TEST_PATH}"
                echo "并发: ${params.PARALLEL_WORKERS}"
                echo "重试: ${params.RERUNS}"

                sh '''
                    python3 --version
                    pip3 install -r requirements.txt --quiet
                '''
            }
        }

        stage('执行测试') {
            steps {
                // 清理旧报告
                sh "rm -rf ${ALLURE_RESULTS} && mkdir -p ${ALLURE_RESULTS}"

                script {
                    // 构建 pytest 命令
                    def cmd = "python3 -m pytest ${params.TEST_PATH}"
                    cmd += " --env=${params.ENV}"
                    cmd += " --alluredir=${ALLURE_RESULTS}"
                    cmd += " --reruns=${params.RERUNS}"
                    cmd += " --reruns-delay=1"
                    cmd += " -v"

                    // 并发配置
                    if (params.PARALLEL_WORKERS != '1') {
                        cmd += " -n ${params.PARALLEL_WORKERS}"
                    }

                    // 测试范围过滤
                    if (params.TEST_SCOPE != 'all') {
                        cmd += " -m ${params.TEST_SCOPE}"
                    }

                    echo "执行命令: ${cmd}"

                    // 执行测试（不因测试失败而中断 Pipeline）
                    def exitCode = sh(script: cmd, returnStatus: true)
                    if (exitCode != 0) {
                        echo "测试执行完成，存在失败用例 (exit code: ${exitCode})"
                        currentBuild.result = 'UNSTABLE'
                    }
                }
            }
        }

        stage('生成报告') {
            steps {
                allure includeProperties: false,
                       jdk: '',
                       results: [[path: "${ALLURE_RESULTS}"]]
            }
        }

        stage('发送通知') {
            when {
                // 无论成功失败都发送通知
                expression { return true }
            }
            steps {
                script {
                    // 从环境变量或凭据获取 Webhook URL
                    def webhookUrl = env.FEISHU_WEBHOOK ?: ''
                    if (!webhookUrl) {
                        echo "未配置 FEISHU_WEBHOOK，跳过通知"
                        return
                    }

                    // Allure 报告链接（Jenkins 插件生成的路径）
                    def reportUrl = "${env.BUILD_URL}allure/"

                    sh """
                        python3 scripts/send_notification.py \
                            --type feishu \
                            --webhook '${webhookUrl}' \
                            --allure-dir ${ALLURE_RESULTS} \
                            --env ${params.ENV} \
                            --report-url '${reportUrl}'
                    """
                }
            }
        }
    }

    post {
        always {
            echo "=== 测试执行完成 ==="
            // 归档测试结果
            archiveArtifacts artifacts: "${ALLURE_RESULTS}/**", allowEmptyArchive: true
        }

        success {
            echo "✅ 全部用例通过"
        }

        unstable {
            echo "⚠️ 存在失败用例，请查看 Allure 报告"
        }

        failure {
            echo "❌ Pipeline 执行异常"
        }
    }
}
