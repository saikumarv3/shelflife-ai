#!/usr/bin/env bash
# ============================================================
# scripts/backup_db.sh
# Daily PostgreSQL backup for ShelfLife AI (Hetzner server)
#
# Set up as a daily cron job:
#   crontab -e
#   0 3 * * * /opt/shelflife-ai/scripts/backup_db.sh >> /var/log/shelflife-backup.log 2>&1
#
# Usage:
#   bash scripts/backup_db.sh
# ============================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/shelflife}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/shelflife_${TIMESTAMP}.sql.gz"

# Resolve postgres container name (works whether run on host or in compose)
CONTAINER=$(docker ps --filter "name=postgres" --format "{{.Names}}" | head -1)

if [ -z "$CONTAINER" ]; then
  echo "[ERROR] $(date): PostgreSQL container not found. Is Docker running?"
  exit 1
fi

mkdir -p "$BACKUP_DIR"

echo "[INFO] $(date): Starting backup → $BACKUP_FILE"

docker exec "$CONTAINER" \
  pg_dump -U shelflife -d shelflife \
  | gzip > "$BACKUP_FILE"

SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "[INFO] $(date): Backup complete — $SIZE written to $BACKUP_FILE"

# Remove backups older than retention period
DELETED=$(find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -print -delete | wc -l)
if [ "$DELETED" -gt 0 ]; then
  echo "[INFO] $(date): Cleaned up $DELETED old backup(s) older than $RETENTION_DAYS days"
fi

# List remaining backups
echo "[INFO] $(date): Current backups in $BACKUP_DIR:"
ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "  (none)"

echo "[INFO] $(date): Done."
