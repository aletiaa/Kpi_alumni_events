from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_identity
from app.models import ChatLink, Event, KpiImportItem, News, Survey, User
from app.services.translation import TranslationUnavailable, translate_fields

router = APIRouter(prefix="/api/translations", tags=["translations"])


@router.get("/{kind}/{item_id}")
def translate_content(kind: str, item_id: int, db: Session = Depends(get_db), ident=Depends(get_current_identity)):
    admin = bool(ident and ident.role == "admin")
    if kind == "kpi":
        if not admin:
            raise HTTPException(status_code=403)
        item = db.get(KpiImportItem, item_id)
        fields = {key: getattr(item, key) for key in ["title", "excerpt"]} if item else None
    elif kind == "news":
        item = db.get(News, item_id)
        if item and not item.is_published and not admin:
            item = None
        fields = {key: getattr(item, key) or "" for key in ["title", "short_description", "content"]} if item else None
        if fields is not None:
            fields["preview"] = item.short_description or item.content[:220]
            fields["preview_short"] = item.short_description or item.content[:120]
    elif kind == "event":
        item = db.get(Event, item_id)
        fields = {key: getattr(item, key) or "" for key in ["title", "description", "short_description", "location"]} if item else None
        if fields is not None:
            fields["preview"] = item.short_description or item.description
    elif kind == "survey":
        item = db.get(Survey, item_id)
        if item and not item.is_active and not admin:
            item = None
        fields = {"title": item.title, "description": item.description or ""} if item else None
        if item:
            for q in item.questions:
                fields[f"question_{q.id}"] = q.question_text
                for index, option in enumerate([s for s in (q.options_text or "").splitlines() if s.strip()]):
                    fields[f"option_{q.id}_{index}"] = option.strip()
    elif kind == "chat":
        item = db.get(ChatLink, item_id)
        fields = {"title": item.title, "description": item.description or ""} if item and (item.is_active or admin) else None
    elif kind == "profile":
        item = db.get(User, item_id)
        fields = {key: getattr(item, key) or "" for key in ["bio", "status", "specialty", "faculty", "skills", "mentorship_topics", "current_position", "city_country", "help_topics", "company"]} if item and item.is_profile_public and item.is_active and not item.is_blocked else None
        if fields is not None:
            fields["position"] = item.current_position or item.status or item.role
    else:
        raise HTTPException(status_code=404)
    if fields is None:
        raise HTTPException(status_code=404)
    try:
        return {"fields": translate_fields(db, fields), "language": "en"}
    except TranslationUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
