"""Private SQLite bundles, verified by restoring a copy, never into the live database."""
import asyncio
import hashlib
import json
import logging
import os
import re
import sqlite3
import tarfile
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.engine import make_url
from app.config import DATABASE_URL, BASE_DIR, ADMINS_CSV_PATH
from app.models import BackupRecord

log = logging.getLogger(__name__)
SETTINGS = ("APP_BASE_URL", "DATABASE_URL", "SECRET_KEY", "EMAIL_ENABLED", "SMTP_HOST",
            "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_TLS", "EMAIL_FROM_EMAIL",
            "TELEGRAM_ENABLED", "TELEGRAM_BOT_TOKEN", "DEEPL_API_KEY", "IOT_API_KEY")


def backup_directory():
    url = make_url(DATABASE_URL)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("SQLite file required")
    return Path(url.database).resolve().parent / "backups"


def backup_path(record):
    if not re.fullmatch(r"backup-\d{8}-\d{6}-[a-f0-9]{8}\.tar\.gz", record.filename):
        raise ValueError("Invalid backup name")
    return backup_directory() / record.filename


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_backup(record):
    path = backup_path(record)
    if checksum(path) != record.checksum:
        raise ValueError("Checksum mismatch")
    with tarfile.open(path, "r:gz") as archive, tempfile.TemporaryDirectory() as directory:
        member = archive.getmember("database.sqlite")
        if not member.isfile():
            raise ValueError("Invalid database member")
        stream = archive.extractfile(member)
        restored = Path(directory) / "restored.sqlite"
        with restored.open("wb") as output:
            import shutil
            shutil.copyfileobj(stream, output)
        with closing(sqlite3.connect(restored)) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Database integrity failure")
            if not connection.execute("SELECT name FROM sqlite_master WHERE name='users'").fetchone():
                raise ValueError("Application schema missing")
    record.verified_at = datetime.utcnow()


def create_backup(db):
    directory = backup_directory()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    import secrets
    filename = "backup-" + datetime.utcnow().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(4) + ".tar.gz"
    path = directory / filename
    with tempfile.TemporaryDirectory() as temporary:
        snapshot = Path(temporary) / "database.sqlite"
        with closing(sqlite3.connect(make_url(DATABASE_URL).database)) as source, closing(sqlite3.connect(snapshot)) as target:
            source.backup(target)
        settings = Path(temporary) / "settings.json"
        from dotenv import dotenv_values
        values = {**dotenv_values(BASE_DIR / ".env"), **os.environ}
        settings.write_text(json.dumps({k:values[k] for k in SETTINGS if k in values}), encoding="utf-8")
        try:
            with path.open("xb") as output:
                os.chmod(path, 0o600)
                with tarfile.open(fileobj=output, mode="w:gz") as archive:
                    archive.add(snapshot, arcname="database.sqlite")
                    archive.add(settings, arcname="settings.json")
                    admins = Path(ADMINS_CSV_PATH)
                    if admins.is_file() and not admins.is_symlink():
                        archive.add(admins, arcname="admins.csv")
                    uploads = BASE_DIR / "app/static/uploads"
                    if uploads.exists():
                        for item in uploads.rglob("*"):
                            if item.is_file() and not item.is_symlink() and item.resolve().is_relative_to(uploads.resolve()):
                                archive.add(item, arcname="uploads/" + item.relative_to(uploads).as_posix())
            record = BackupRecord(filename=filename, checksum=checksum(path))
            verify_backup(record)
            db.add(record)
            db.commit()
            prune_backups(db)
            return record
        except Exception:
            path.unlink(missing_ok=True)
            raise


def daily_backup(factory):
    with factory() as db:
        last = db.query(BackupRecord).order_by(BackupRecord.created_at.desc()).first()
        if not last or last.created_at < datetime.utcnow() - timedelta(hours=24):
            create_backup(db)


def prune_backups(db):
    directory = backup_directory().resolve()
    older = db.query(BackupRecord).order_by(BackupRecord.created_at.desc(), BackupRecord.id.desc()).offset(14).all()
    for record in older:
        path = backup_path(record)
        if path.is_symlink() or path.resolve().parent != directory:
            raise ValueError("Unsafe backup path")
        path.unlink(missing_ok=True)
        db.delete(record)
    db.commit()


async def backup_loop(factory):
    while True:
        try:
            await asyncio.to_thread(daily_backup, factory)
        except Exception:
            log.error("Automatic backup failed; administrator intervention required")
        await asyncio.sleep(3600)
