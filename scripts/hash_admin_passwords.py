"""One-time local migration; never prints credentials or stores plaintext backups."""
import csv
import os
import tempfile
from pathlib import Path

from app.config import ADMINS_CSV_PATH
from app.security import hash_password, pwd_context


def migrate(path):
    path = Path(path)
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    converted = []
    for row in rows:
        encoded = row.get("password_hash", "")
        if not pwd_context.identify(encoded):
            password = row.get("password", "")
            if not password:
                raise ValueError("Administrator has no usable password")
            encoded = hash_password(password)
        converted.append(dict(email=row["email"], password_hash=encoded,
                              full_name=row.get("full_name") or "Admin"))
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=["email", "password_hash", "full_name"])
            writer.writeheader()
            writer.writerows(converted)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return len(converted)


if __name__ == "__main__":
    print("Administrator records secured:", migrate(ADMINS_CSV_PATH))
