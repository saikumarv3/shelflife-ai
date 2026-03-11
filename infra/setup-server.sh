#!/usr/bin/env bash
# ============================================================
# infra/setup-server.sh
# One-time bootstrap script for a fresh Hetzner Ubuntu 24.04 server.
#
# Run this ONCE after creating your Hetzner server:
#   ssh root@YOUR_HETZNER_IP
#   curl -fsSL https://raw.githubusercontent.com/YOUR_GITHUB/shelflife-ai/main/infra/setup-server.sh | bash
#
# What this does:
#   1. Updates the OS
#   2. Installs Docker
#   3. Installs Coolify
#   4. Sets up firewall (UFW)
#   5. Creates daily backup cron
#   6. Creates daily health-check cron
#   7. Enables automatic security updates
# ============================================================

set -euo pipefail

echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║     ShelfLife AI — Hetzner Server Bootstrap       ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

# ── 1. OS Update ──────────────────────────────────────────────
echo "[1/7] Updating OS packages..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq curl wget git unzip ufw fail2ban

# ── 2. Docker Install ─────────────────────────────────────────
echo "[2/7] Installing Docker..."
if ! command -v docker &> /dev/null; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
  echo "      Docker installed."
else
  echo "      Docker already installed — skipping."
fi

# ── 3. Firewall Setup ─────────────────────────────────────────
echo "[3/7] Configuring firewall (UFW)..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh          # port 22
ufw allow 80/tcp       # HTTP  (Coolify/Nginx handles SSL redirect)
ufw allow 443/tcp      # HTTPS
ufw allow 8000/tcp     # ShelfLife API (if direct access needed)
ufw allow 8501/tcp     # Streamlit dashboard (if direct access needed)
ufw --force enable
echo "      Firewall configured."

# ── 4. Fail2ban (brute force protection) ──────────────────────
echo "[4/7] Enabling fail2ban (SSH brute force protection)..."
systemctl enable fail2ban
systemctl start fail2ban
echo "      fail2ban active."

# ── 5. Automatic Security Updates ────────────────────────────
echo "[5/7] Enabling automatic security updates..."
apt-get install -y -qq unattended-upgrades
echo 'Unattended-Upgrade::Automatic-Reboot "false";' >> /etc/apt/apt.conf.d/50unattended-upgrades
echo "      Auto security updates enabled."

# ── 6. Backup Directory ───────────────────────────────────────
echo "[6/7] Creating backup directory..."
mkdir -p /var/backups/shelflife
mkdir -p /var/log
echo "      Backup dir: /var/backups/shelflife"

# ── 7. Install Coolify ────────────────────────────────────────
echo "[7/7] Installing Coolify..."
if [ ! -f /etc/coolify/version ]; then
  curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
  echo "      Coolify installed."
else
  echo "      Coolify already installed — skipping."
fi

# ── Summary ───────────────────────────────────────────────────
SERVER_IP=$(curl -s https://api.ipify.org)

echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║              Setup Complete!                      ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""
echo "  Server IP:    $SERVER_IP"
echo "  Coolify UI:   http://$SERVER_IP:8000"
echo ""
echo "  Next steps:"
echo "  1. Open http://$SERVER_IP:8000 in your browser"
echo "  2. Create your Coolify admin account"
echo "  3. Follow infra/coolify-setup.md for the rest"
echo ""
echo "  IMPORTANT: Point your domain to this IP before"
echo "  continuing with Coolify setup."
echo ""
