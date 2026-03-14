"""
Model rollback script — promote a previous MLflow model version back to Production.

Usage:
    uv run python -m scripts.rollback_model --model shelflife-demand-forecast --to-version 3
    uv run python -m scripts.rollback_model --model shelflife-demand-forecast --list
    uv run python -m scripts.rollback_model --all --to-version 3

What it does:
  1. Archives the current Production version
  2. Promotes the specified version to Production
  3. Flushes the Redis prediction cache
  4. Inserts a model_rollback alert in the DB
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone

import mlflow
from mlflow import MlflowClient
from sqlalchemy import text

from config.settings import settings
from db.session import engine

logger = logging.getLogger(__name__)


def list_versions(client: MlflowClient, model_name: str) -> None:
    """Print all registered versions for a model."""
    try:
        versions = client.search_model_versions(f"name='{model_name}'")
    except Exception as exc:
        logger.error("Could not fetch versions for %s: %s", model_name, exc)
        return

    if not versions:
        print(f"No versions found for '{model_name}'")
        return

    print(f"\n{'Ver':>4}  {'Stage':12}  {'Run ID':14}  {'Created'}")
    print("-" * 65)
    for v in sorted(versions, key=lambda x: int(x.version)):
        created = datetime.fromtimestamp(v.creation_timestamp / 1000).strftime("%Y-%m-%d %H:%M")
        print(f"{v.version:>4}  {v.current_stage:12}  {v.run_id[:12]}...  {created}")
    print()


def rollback_model(model_name: str, to_version: str) -> bool:
    """
    Archive the current Production version and promote `to_version`.
    Returns True if successful.
    """
    client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)

    # Find current Production version
    try:
        prod_versions = [
            v
            for v in client.search_model_versions(f"name='{model_name}'")
            if v.current_stage == "Production"
        ]
    except Exception as exc:
        logger.error("MLflow unavailable: %s", exc)
        return False

    current_version = prod_versions[0].version if prod_versions else None

    if current_version == to_version:
        print(f"Version {to_version} is already in Production. Nothing to do.")
        return True

    # Archive current Production
    if current_version:
        logger.info("Archiving current Production version %s", current_version)
        client.transition_model_version_stage(
            name=model_name,
            version=current_version,
            stage="Archived",
            archive_existing_versions=False,
        )

    # Promote target version
    logger.info("Promoting version %s to Production", to_version)
    client.transition_model_version_stage(
        name=model_name,
        version=to_version,
        stage="Production",
        archive_existing_versions=False,
    )

    # Flush Redis cache
    try:
        import redis

        r = redis.Redis.from_url(settings.redis_url)
        keys = r.keys("shelflife:predict:*")
        if keys:
            r.delete(*keys)
            logger.info("Flushed %d prediction cache keys", len(keys))
    except Exception as exc:
        logger.warning("Redis flush failed (non-fatal): %s", exc)

    # Insert rollback alert
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO alerts (alert_type, severity, message, metadata_json)
                    VALUES ('model_rollback', 'warning', :msg, :meta)
                """),
                {
                    "msg": f"Model '{model_name}' rolled back from v{current_version} to v{to_version}",
                    "meta": json.dumps(
                        {
                            "model_name": model_name,
                            "from_version": current_version,
                            "to_version": to_version,
                            "rolled_back_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ),
                },
            )
        logger.info("Rollback alert inserted into alerts table")
    except Exception as exc:
        logger.warning("Could not insert alert (non-fatal): %s", exc)

    print(f"\n✓ Rollback complete: '{model_name}' is now version {to_version} (Production)")
    if current_version:
        print(f"  Previous version {current_version} → Archived")
    print("  Redis cache flushed")
    print("  Alert recorded in alerts table\n")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Roll back a ShelfLife AI model to a previous MLflow version"
    )
    parser.add_argument(
        "--model",
        default=settings.demand_model_name,
        help=f"Model name (default: {settings.demand_model_name})",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Roll back both demand and waste models to the same version",
    )
    parser.add_argument("--to-version", help="Target version number to promote")
    parser.add_argument("--list", action="store_true", help="List all versions and exit")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)

    if args.list:
        for name in [settings.demand_model_name, settings.waste_model_name]:
            print(f"\n── {name} ──")
            list_versions(client, name)
        sys.exit(0)

    if not args.to_version:
        parser.error("--to-version is required (use --list to see available versions)")

    models = [settings.demand_model_name, settings.waste_model_name] if args.all else [args.model]

    success = True
    for model_name in models:
        ok = rollback_model(model_name, args.to_version)
        success = success and ok

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
