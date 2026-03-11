#!/usr/bin/env bash
# ============================================================
# scripts/healthcheck_prod.sh
# Checks all ShelfLife AI services are healthy on production.
#
# Usage:
#   bash scripts/healthcheck_prod.sh [your-domain.com]
#
# Example:
#   bash scripts/healthcheck_prod.sh api.yourdomain.com
#
# Set up as a cron (every 5 min) for basic uptime monitoring:
#   */5 * * * * /opt/shelflife-ai/scripts/healthcheck_prod.sh api.yourdomain.com >> /var/log/shelflife-health.log 2>&1
# ============================================================

set -euo pipefail

API_DOMAIN="${1:-localhost:8000}"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
FAILED=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "[$TIMESTAMP] ✅  $name — OK"
  else
    echo "[$TIMESTAMP] ❌  $name — FAILED"
    FAILED=$((FAILED + 1))
  fi
}

echo "[$TIMESTAMP] ── ShelfLife AI Health Check ──────────────────"

# Docker containers running
check "PostgreSQL container" "docker ps --filter name=postgres --filter status=running | grep -q postgres"
check "Redis container"      "docker ps --filter name=redis --filter status=running | grep -q redis"
check "MLflow container"     "docker ps --filter name=mlflow --filter status=running | grep -q mlflow"
check "API container"        "docker ps --filter name=api --filter status=running | grep -q api"
check "Dashboard container"  "docker ps --filter name=dashboard --filter status=running | grep -q dashboard"

# Service-level health
check "PostgreSQL ping"  "docker exec \$(docker ps --filter name=postgres -q) pg_isready -U shelflife"
check "Redis ping"       "docker exec \$(docker ps --filter name=redis -q) redis-cli ping"
check "API /health"      "curl -sf https://${API_DOMAIN}/health"
check "API /ready"       "curl -sf https://${API_DOMAIN}/ready"

# Disk space warning (warn if >80% full)
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -gt 80 ]; then
  echo "[$TIMESTAMP] ⚠️  Disk usage at ${DISK_USAGE}% — consider cleanup"
  FAILED=$((FAILED + 1))
else
  echo "[$TIMESTAMP] ✅  Disk usage ${DISK_USAGE}% — OK"
fi

# RAM usage warning (warn if >85%)
RAM_USAGE=$(free | awk '/^Mem:/ {printf "%.0f", $3/$2*100}')
if [ "$RAM_USAGE" -gt 85 ]; then
  echo "[$TIMESTAMP] ⚠️  RAM usage at ${RAM_USAGE}% — consider upgrading server"
else
  echo "[$TIMESTAMP] ✅  RAM usage ${RAM_USAGE}% — OK"
fi

echo "[$TIMESTAMP] ─────────────────────────────────────────────────"

if [ "$FAILED" -gt 0 ]; then
  echo "[$TIMESTAMP] ❌  $FAILED check(s) FAILED"
  exit 1
else
  echo "[$TIMESTAMP] ✅  All checks passed"
  exit 0
fi
