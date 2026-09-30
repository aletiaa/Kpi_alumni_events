import hashlib
import json
import re
import threading
from urllib.request import Request, urlopen

from sqlalchemy.exc import IntegrityError

from app.config import DEEPL_API_KEY
from app.models import ContentTranslation

_lock = threading.Lock()
CYRILLIC = re.compile(r"[А-Яа-яІіЇїЄєҐґ]")


class TranslationUnavailable(Exception):
    pass


def deepl_translate(texts):
    if not DEEPL_API_KEY:
        raise TranslationUnavailable("not_configured")
    host = "api-free.deepl.com" if DEEPL_API_KEY.endswith(":fx") else "api.deepl.com"
    payload = json.dumps({"text": texts, "target_lang": "EN-GB"}).encode("utf-8")
    if len(payload) > 120000:
        raise TranslationUnavailable("content_too_long")
    request = Request(f"https://{host}/v2/translate", data=payload, headers={
        "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}", "Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read(2000001)
        if len(raw) > 2000000:
            raise ValueError("Response too large")
        data = json.loads(raw)
        result = [row["text"] for row in data["translations"]]
        if len(result) != len(texts) or any(not isinstance(t, str) or not t.strip() for t in result):
            raise ValueError("Invalid translations")
        return result
    except Exception as exc:
        # Never return provider errors, request headers, or credentials to clients.
        raise TranslationUnavailable("temporarily_unavailable") from exc


def translate_fields(db, fields):
    result = dict(fields)
    with _lock:
        missing = {}
        for field, text in fields.items():
            if not text or not CYRILLIC.search(text):
                continue
            digest = hashlib.sha256(("deepl:en-gb:v1:" + text).encode("utf-8")).hexdigest()
            cached = db.get(ContentTranslation, digest)
            if cached:
                result[field] = cached.english
            else:
                missing.setdefault(digest, {"text": text, "fields": []})["fields"].append(field)
        entries = list(missing.items())
        for offset in range(0, len(entries), 50):
            batch = entries[offset:offset + 50]
            translated = deepl_translate([row["text"] for _, row in batch])
            for (digest, row), english in zip(batch, translated):
                for field in row["fields"]:
                    result[field] = english
                try:
                    with db.begin_nested():
                        db.add(ContentTranslation(source_hash=digest, english=english))
                        db.flush()
                except IntegrityError:
                    pass
            db.commit()
    return result
