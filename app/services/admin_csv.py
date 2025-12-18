import csv
from dataclasses import dataclass
from typing import Optional
from ..config import ADMINS_CSV_PATH

@dataclass
class AdminRecord:
    email: str
    password: str
    full_name: str

def find_admin_by_email(email: str) -> Optional[AdminRecord]:
    email_n = (email or "").strip().lower()
    with open(ADMINS_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row.get("email", "").strip().lower()) == email_n:
                return AdminRecord(
                    email=email_n,
                    password=(row.get("password", "") or "").strip(),
                    full_name=(row.get("full_name", "") or "Admin").strip()
                )
    return None
