pipeline {
    agent any

    environment {
        COMPOSE_FILE = 'docker-compose.yml'
    }

    triggers {
        githubPush()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo " Code checked out successfully"
            }
        }

        stage('Lint & Test') {
            parallel {
                stage('Go Backend') {
                    steps {
                        dir('backend-go') {
                            sh 'go vet ./...'
                            sh 'go test ./... -v'
                        }
                    }
                }
                stage('Python Trainer') {
                    steps {
                        dir('trainer') {
                            sh '''
                                pip3 install -r requirements.txt --quiet
                                pip3 install pytest httpx --quiet
                                # Run unit tests (ignoring model load / inference test)
                                pytest test_app.py -v -k "not inference"
                            '''
                        }
                    }
                }
            }
        }

        stage('Build Docker Images') {
            steps {
                echo "Building Docker images using Docker Compose..."
                sh 'docker compose -f ${COMPOSE_FILE} build'
            }
        }

        stage('Deploy') {
            steps {
                echo " Starting services..."
                sh 'docker compose -f ${COMPOSE_FILE} up -d'
                echo " Waiting for services to initialize..."
                sleep 10
            }
        }

        stage('Health Checks') {
            steps {
                echo " Running API health check..."
                sh 'curl -sf http://localhost:8081/health || (echo " Go API is down" && exit 1)'

                echo " Running Trainer health check..."
                sh 'curl -sf http://localhost:8000/health || (echo " Python Trainer is down" && exit 1)'

                echo " Running Frontend health check..."
                sh 'curl -sf http://localhost:80 || (echo " Frontend is down" && exit 1)'

                echo " All services are healthy!"
            }
        }
    }

    post {
        always {
            echo " Fetching Docker Compose logs..."
            sh 'docker compose -f ${COMPOSE_FILE} logs --no-color > compose_logs.txt 2>&1 || true'
            archiveArtifacts artifacts: 'compose_logs.txt', allowEmptyArchive: true
        }
        cleanup {
            echo " Stopping and removing containers..."
            sh 'docker compose -f ${COMPOSE_FILE} down --remove-orphans || true'
        }
    }
}
