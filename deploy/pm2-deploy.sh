#!/usr/bin/env bash
# Run on the VPS after code is updated (used by GitHub Actions SSH deploy).
set -euo pipefail

DEPLOY_PATH="${DEPLOY_PATH:-/opt/agvisely}"
cd "$DEPLOY_PATH"

echo "==> Git pull"
git fetch origin main
git reset --hard origin/main

echo "==> Python deps"
if [[ ! -d venv ]]; then
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Frontend build"
cd frontend
npm ci
npm run build
cd ..

echo "==> PM2 reload"
if ! command -v pm2 >/dev/null 2>&1; then
  npm install -g pm2
fi

pm2 startOrReload ecosystem.config.cjs --update-env
pm2 save

echo "==> Status"
pm2 status
curl -fsS "http://127.0.0.1:9603/" || true
