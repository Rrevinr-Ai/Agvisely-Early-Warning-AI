# One-time PM2 setup on the VPS (Ubuntu). Run as root or with sudo where needed.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Rrevinr-Ai/Agvisely-Early-Warning-AI.git}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/agvisely}"

echo "==> Install Node.js 20 + PM2 (if missing)"
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi
npm install -g pm2

echo "==> Install Python venv tools"
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git

echo "==> Clone repo to ${DEPLOY_PATH}"
if [[ ! -d "${DEPLOY_PATH}/.git" ]]; then
  git clone "$REPO_URL" "$DEPLOY_PATH"
fi

cd "$DEPLOY_PATH"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "EDIT ${DEPLOY_PATH}/.env before starting (DATABASE_URL, OPENAI_API_KEY, ...)"
fi

python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
pip install -r requirements.txt

cd frontend
npm ci
npm run build
cd ..

# Open ports
if command -v ufw >/dev/null 2>&1; then
  ufw allow 9603/tcp || true
  ufw allow 9604/tcp || true
fi

pm2 start ecosystem.config.cjs
pm2 save
pm2 startup systemd -u "$(whoami)" --hp "$HOME" || true

echo "==> Done. Backend :9603  Frontend :9604"
pm2 status
