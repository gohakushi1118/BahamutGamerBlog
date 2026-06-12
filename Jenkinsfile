pipeline {
    agent any

    parameters {
        string(name: 'OWNER',  defaultValue: '',
               description: 'REQUIRED — Bahamut owner ID to scrape (the ?owner= value)')
        string(name: 'BRANCH', defaultValue: 'main',
               description: 'Branch to push the synced posts to')
    }

    triggers {
        cron('H 4 * * *')
    }

    options {
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    environment {
        DOCKER_IMAGE   = 'python:3.12-slim'
        CREDENTIALS_ID = 'github-pat'
    }

    stages {
        stage('Validate') {
            steps {
                script {
                    if (!params.OWNER?.trim()) {
                        error('OWNER parameter is empty. Set the Bahamut owner ID to scrape.')
                    }
                }
            }
        }

        stage('Sync (Docker)') {
            steps {
                withCredentials([usernamePassword(
                        credentialsId: env.CREDENTIALS_ID,
                        usernameVariable: 'GH_USER',
                        passwordVariable: 'GH_TOKEN')]) {
                    // Capture this repo's origin URL, then run sync.sh inside the
                    // container. The workspace is mounted read-only (only to read
                    // sync.sh); `tr -d` strips any CR so CRLF-committed files work.
                    bat '''
                        for /f "delims=" %%i in ('git remote get-url origin') do set "ORIGIN_URL=%%i"
                        docker run --rm ^
                            -e OWNER=%OWNER% -e BRANCH=%BRANCH% ^
                            -e GH_USER=%GH_USER% -e GH_TOKEN=%GH_TOKEN% ^
                            -e ORIGIN_URL=%ORIGIN_URL% ^
                            -v "%CD%":/src:ro -w /src ^
                            %DOCKER_IMAGE% sh -c "cat /src/sync.sh | tr -d '\\r' | sh"
                    '''
                }
            }
        }
    }

    post {
        success { echo 'success!' }
        failure { echo 'failure!' }
    }
}
