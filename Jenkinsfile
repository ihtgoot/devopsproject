pipeline {
    agent any

    environment {
        COMPOSE_FILE = 'docker-compose.yml'
        GO_SERVICE   = 'backend-go'
        PY_SERVICE   = 'trainer'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                echo "✅ Code checked out"
            }
        }

        stage('Lint') {
            parallel {
                stage('Go Lint') {
                    steps {
                        dir('backend-go') {
                            sh '''
                                go vet ./...
                                echo "Go vet passed"
                            '''
                        }
                    }
                }
                stage('Python Lint') {
                    steps {
                        dir('trainer') {
                            sh '''
                                pip3 install --quiet flake8
                                flake8 app.py train.py --max-line-length=120 --ignore=E501,W503
                                echo "Flake8 passed"
                            '''
                        }
                    }
                }
            }
        }

        stage('Test') {
            parallel {
                stage('Go Tests') {
                    steps {
                        dir('backend-go') {
                            sh 'go test ./... -v -count=1'
                        }
                    }
                }
                stage('Python Smoke Test') {
                    steps {
                        dir('trainer') {
                            sh '''
                                pip3 install --quiet flask
                                python3 -c "from app import app; print('Flask app imports OK')"
                            '''
                        }
                    }
                }
            }
        }

        stage('Build Images') {
            steps {
                sh 'docker compose -f ${COMPOSE_FILE} build --no-cache'
                echo "✅ All images built"
            }
        }

        stage('Deploy (Compose Up)') {
            steps {
                sh 'docker compose -f ${COMPOSE_FILE} up -d'
                echo "✅ Services started"
                sh 'sleep 10'
            }
        }

        stage('Health Checks') {
            steps {
                sh '''
                    echo "Checking Go API..."
                    curl -sf http://localhost:8080/health || (echo "❌ API health check failed" && exit 1)
                    echo "✅ API OK"

                    echo "Checking Trainer..."
                    curl -sf http://localhost:8000/health || (echo "❌ Trainer health check failed" && exit 1)
                    echo "✅ Trainer OK"

                    echo "Checking Frontend..."
                    curl -sf http://localhost:80 || (echo "❌ Frontend health check failed" && exit 1)
                    echo "✅ Frontend OK"
                '''
            }
        }
    }

    post {
        always {
            sh 'docker compose -f ${COMPOSE_FILE} logs --no-color > compose_logs.txt 2>&1 || true'
            archiveArtifacts artifacts: 'compose_logs.txt', allowEmptyArchive: true
        }
        success {
            echo "🎉 Pipeline passed. All services healthy."
        }
        failure {
            echo "💥 Pipeline failed. Bringing down services."
            sh 'docker compose -f ${COMPOSE_FILE} down --remove-orphans || true'
        }
        cleanup {
            sh 'docker compose -f ${COMPOSE_FILE} down --remove-orphans || true'
            echo "🧹 Cleanup done."
        }
    }
}
