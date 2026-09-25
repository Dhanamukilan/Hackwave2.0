pipeline {
    agent any

    environment {
        PYTHONPATH = '.'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'pip install -r backend/requirements.txt'
            }
        }

        stage('Run Test Suite') {
            steps {
                sh '''
                    mkdir -p results
                    python -m pytest tests/unit/ --junitxml=results/junit.xml || true
                '''
            }
        }
    }

    post {
        always {
            junit testResults: 'results/junit.xml', allowEmptyResults: true
            archiveArtifacts artifacts: 'results/junit.xml', fingerprint: true, allowEmptyArchive: true
        }
    }
}
