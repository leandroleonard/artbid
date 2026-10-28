"""Bootstrap application

Use:
    python -m scripts.bootstrap
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from alembic import command 
from alembic.config import Config 
from sqlalchemy import create_engine, text

from app.core.config import settings


def wait_for_database(attempts: int = 40, delay: float = 2.0) -> None:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            engine.dispose()
            return
        except Exception as exc: 
            last_error = exc
            print(f"[bootstrap] postgres indisponivel ({attempt + 1}/{attempts}): {type(exc).__name__}")
            time.sleep(delay)
    engine.dispose()
    raise RuntimeError("Base de dados indisponivel") from last_error


def run_migrations() -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(config, "head")
    print("[bootstrap] alembic upgrade head OK")


def apply_audit_guard() -> None:
    import psycopg

    dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    script = (ROOT / "scripts" / "audit.sql").read_text(encoding="utf-8")
    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(script)
    print("[bootstrap] guard de auditoria aplicado")


def run_seed() -> dict | None:
    if os.getenv("SEED_ON_START", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        print("[bootstrap] seed desligado (SEED_ON_START=false)")
        return None
    from scripts.seed import seed

    result = seed()
    print("[bootstrap] seed OK")
    return result


def main() -> None:
    wait_for_database()
    run_migrations()
    apply_audit_guard()
    summary = run_seed()
    print(json.dumps({"migrations": "head", "auditGuard": "applied", "seed": summary}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
