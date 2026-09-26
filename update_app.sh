#!/usr/bin/env bash

set -euo pipefail

APP_DIR="/home/azureuser/azure-rag-chatbot"

cd "$APP_DIR"

export GIT_SSH_COMMAND="ssh -i /home/azureuser/.ssh/github_deploy_key -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"

git pull --ff-only origin main

docker compose pull

docker compose up -d --remove-orphans

docker compose ps