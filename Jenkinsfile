pipeline {
    agent any

    parameters {
        choice(
            name: 'ENV',
            choices: ['dev', 'test', 'staging'],
            description: '选择测试环境'
        )
        choice(
            name: 'TEST_SCOPE',
            choices: ['all', 'smoke', 'regression', 'p0'],
            description: '测试范围'
        )
        string(
            name: 'PARALLEL_WORKERS',
            defaultValue: '4',
            description: '并发 Worker 数量'
        )
        string(
            name: 'RERUNS',
            defaultValue: '2',
            description: '失败重试次数'
        )
    }

    environment {
        PYTHON_VERSION = '3.10'
        ALLURE_RESULTS = 'reports/allure-results'
    }

    stages {
        stage('环境准备') {
            steps {
                echo "=== 安装依赖 ==="
                sh 'python3 -m pip install -r requirements.txt'
            }
        }

        stage('执行测试') {
            steps {
                script {
                    def markers = ''
                    if (params.TEST_SCOPE != 'all') {
                        markers = "-m ${params.TEST_SCOPE}"
                    }

                    sh """
                        python3 -m pytest testcases/ \
                            --env=${params.ENV} \
                            -n ${params.PARALLEL_WORKERS} \
                            --reruns=${params.RERUNS} \
                            --reruns-delay=1 \
                            --alluredir=${ALLURE_RESULTS} \
                            -v \
                            ${markers}
                    """
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
    }

    post {
        always {
            echo "=== 测试执行完成 ==="
            // 归档测试结果
            archiveArtifacts artifacts: "${ALLURE_RESULTS}/**", allowEmptyArchive: true
        }

        failure {
            echo "=== 测试失败，发送通知 ==="
            // 可在此处调用钉钉/企业微信通知脚本
            // sh 'python3 scripts/send_notification.py --type=dingtalk'
        }

        success {
            echo "=== 测试全部通过 ==="
        }
    }
}
