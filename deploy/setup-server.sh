#!/usr/bin/env bash
# One-time VPS setup. Run as root (or with sudo) on Ubuntu/Debian:
#   curl -fsSL ... | bash
# or copy this file to the server and: bash setup-server.sh

set -euo pipefail

DEPLOY_DIR=/opt/agvisely

echo "==> Installing Docker (if missing)..."
if ! command -v docker >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

echo "==> Creating ${DEPLOY_DIR}..."
mkdir -p "${DEPLOY_DIR}"
chmod 755 "${DEPLOY_DIR}"

if [[ ! -f "${DEPLOY_DIR}/docker-compose.yml" ]]; then
  echo "ERROR: Copy deploy/docker-compose.yml to ${DEPLOY_DIR}/docker-compose.yml first."
  exit 1
fi

if [[ ! -f "${DEPLOY_DIR}/.env" ]]; then
  echo "ERROR: Copy deploy/.env.example to ${DEPLOY_DIR}/.env and edit secrets."
  exit 1
fi

echo "==> Opening firewall ports 9603 and 9604 (if ufw is active)..."
if command -v ufw >/dev/null 2>&1; then
  ufw allow 9603/tcp || true
  ufw allow 9604/tcp || true
fi

echo "==> Done. Next:"
echo "  1. Edit ${DEPLOY_DIR}/.env"
echo "  2. docker login ghcr.io -u YOUR_GITHUB_USER"
echo "  3. cd ${DEPLOY_DIR} && docker compose pull && docker compose up -d"
echo "  4. Add GitHub secrets DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_KEY, GHCR_TOKEN"
