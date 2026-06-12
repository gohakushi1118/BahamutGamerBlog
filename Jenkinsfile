// Jenkins Pipeline: Scrape Bahamut 小屋 creations → Markdown → commit & push.
//
// Everything (clone, scrape, commit, push) happens INSIDE a python:3.12-slim
// Linux container via sync.sh. The container clones the repo fresh and pushes
// directly, so nothing is written back to the Jenkins workspace.
//
// Why this design: on a Windows Jenkins host, a bind-mounted workspace is
// effectively read-only to a Linux container (root can neither overwrite nor
// delete host files). So the workspace is mounted read-only and used only to
// read sync.sh; all work happens in the container's own filesystem.
//
// One-time setup (Jenkins UI):
//   1. Plugins: Pipeline, Git. Docker installed & running on the Jenkins host.
//   2. Credentials → "Username with password":
//        ID: github-pat | Username: <your-github-username> | Password: <GitHub PAT, repo scope>
//   3. New Item → Pipeline → "Pipeline script from SCM" → your fork, Script Path: Jenkinsfile.
//   4. Run with "Build with Parameters" and set OWNER. Adjust the cron below as needed.

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
