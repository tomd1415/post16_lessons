# Deploying post16_lessons on Proxmox (VM-based)

These steps assume Proxmox VE 7/8 with a standard `vmbr0` bridge. We deploy a Debian 12 VM, install Docker, and run the stack with Docker Compose.

## 1) Create a VM in Proxmox
- **Template:** Debian 12 cloud image or ISO (Ubuntu 22.04+ is also fine).
- **Resources (baseline):** 2 vCPU, 4–6 GB RAM, 20–40 GB disk. Increase RAM/CPU if you expect many concurrent runners.
- **Network:** Use `vmbr0` (or your main bridge). Plan a static IP (via cloud-init or `/etc/network/interfaces.d`).
- **Options:**
  - Enable **QEMU guest agent** (recommended).
  - If you want container-in-VM optimizations, enable **nested virtualization** on the VM CPU (Proxmox: `Options → Nested` or `qm set <VMID> -cpu host,+vmx` / `+svm`).
- **Cloud-init (optional):** Preseed SSH keys and a non-root user.

## 2) OS post-install on the VM
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git ca-certificates gnupg lsb-release
```

## 3) Install Docker Engine + Compose plugin
```bash
# Docker repo
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Optional: let your user manage Docker (relog to take effect)
sudo usermod -aG docker $USER
```

## 4) Clone the project
```bash
mkdir -p ~/apps && cd ~/apps
git clone https://github.com/<your-org>/post16_lessons.git
cd post16_lessons
```

## 5) Runtime configuration
- **Docker socket:** The Python runner uses Docker-in-Docker to execute sandboxed code. Ensure the API container can reach the host socket. Default is `unix:///var/run/docker.sock` (mounted by Compose).
- **Environment:** If you need overrides, copy `compose.yml` env vars into a `.env` file (e.g., `RUNNER_TIMEOUT_SEC`, `RUNNER_MEMORY_MB`, `RUNNER_CPUS`, `RUNNER_IMAGE`). Defaults usually work.
- **TLS / reverse proxy:** `docker/Caddyfile` is included. For public HTTPS, point DNS at the VM and set `email` + hosts in the Caddyfile (or terminate TLS at a Proxmox/LB front end).
- **Data:** Review any bind mounts/volumes in `compose.yml` and ensure the VM disk or attached storage is sized appropriately.

## 6) Build and start
```bash
# From repo root
sudo docker compose up -d --build
```

## 7) Sanity checks
- App: `curl -I http://<vm-ip>:8080` (adjust to your exposed port or Caddy front end).
- Runner diagnostics (teacher/admin): `http://<vm-ip>:8080/api/python/diagnostics` (confirms Docker socket visibility).
- Turtle stub: run a turtle activity; confirm `turtle.svg` appears in “Run files”.

## 8) Maintenance
- **Ops checklist (quick):**
  - Ensure any overrides live in `.env` (for example: `RUNNER_TIMEOUT_SEC`, `RUNNER_MEMORY_MB`, `RUNNER_CPUS`, `RUNNER_IMAGE`, `RUNNER_AUTO_PULL`, `RETENTION_YEARS`).
  - Backups: run `scripts/backup.sh`, copy the backup off the VM, and test restore with `scripts/restore.sh <backup_dir> --force` on a schedule.
  - Upgrade flow: `git pull` -> `sudo docker compose build --pull` -> `sudo docker compose up -d`.
  - Post-upgrade checks: `/api/health` and `/api/python/diagnostics`.
- **Update app:**
  ```bash
  git pull
  sudo docker compose build --pull
  sudo docker compose up -d
  ```
- **Backups:** Use Proxmox snapshots or `scripts/backup.sh` (creates `backups/backup_YYYYMMDD_HHMMSS`). Restore with `scripts/restore.sh <backup_dir> --force`.
- **Logs:** `sudo docker compose logs -f api` (and other services as needed).

## 9) Troubleshooting
- **Docker permission denied:** Ensure your user is in `docker` group or prepend `sudo`.
- **Runner errors:** Check diagnostics endpoint; verify the Docker socket is mounted and the host can pull `RUNNER_IMAGE` (default `python:3.12-slim`).
- **No turtle SVG:** Confirm the runner was rebuilt after code changes (`docker compose up -d --build`) and the activity shows “Run files”.
- **Port conflicts:** Adjust published ports in `compose.yml` or front the stack with a Proxmox/LXC reverse proxy.

## 10) Security hardening
- Keep the VM patched (`unattended-upgrades`), disable password SSH, use keys.
- Enable the Proxmox firewall and/or UFW; allow only HTTP/HTTPS/SSH as needed.
- Limit Docker exposure to the VM; do not expose the Docker socket externally.

---
If you prefer an LXC instead of a VM, use a **privileged** Debian 12 container with nesting (for Docker) and mount `/var/run/docker.sock`. VM is recommended for clearer isolation.
