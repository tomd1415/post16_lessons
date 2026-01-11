#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run with sudo: sudo $0" >&2
  exit 1
fi

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_DIR=${REPO_DIR:-"$(cd "$SCRIPT_DIR/.." && pwd)"}
RUN_UPGRADE=${RUN_UPGRADE:-0}
START_STACK=${START_STACK:-1}
ADD_USER_TO_DOCKER_GROUP=${ADD_USER_TO_DOCKER_GROUP:-1}

if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  if [[ "${ID:-}" != "debian" ]]; then
    echo "Warning: This script targets Debian. Detected: ${ID:-unknown}." >&2
  fi
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
if [[ "$RUN_UPGRADE" -eq 1 ]]; then
  apt-get upgrade -y
fi

apt-get install -y ca-certificates curl gnupg lsb-release git

install -m 0755 -d /etc/apt/keyrings
if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
  curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
fi

ARCH=$(dpkg --print-architecture)
CODENAME=$(lsb_release -cs)
echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian ${CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

if [[ "$ADD_USER_TO_DOCKER_GROUP" -eq 1 ]]; then
  if getent group docker >/dev/null; then
    if [[ -n "${SUDO_USER:-}" ]]; then
      usermod -aG docker "$SUDO_USER" || true
      echo "Added $SUDO_USER to the docker group. Log out/in for it to take effect."
    else
      echo "SUDO_USER not set; skipping docker group update."
    fi
  fi
fi

if [[ "$START_STACK" -eq 1 ]]; then
  if [[ -f "$REPO_DIR/compose.yml" ]]; then
    echo "Starting stack from $REPO_DIR"
    cd "$REPO_DIR"
    docker compose up -d --build
  else
    echo "compose.yml not found at $REPO_DIR; skipping docker compose." >&2
  fi
fi

echo "Done."
