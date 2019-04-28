#!/usr/bin/env groovy

node {
    stage('Checkout') {
        checkout scm
        sh 'git clean -fxd'
    }
    stage('Test') {
        echo 'testing...'
        sh './test.py'
    }
}


