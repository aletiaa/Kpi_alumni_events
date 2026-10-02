import logging
from starlette.middleware.base import BaseHTTPMiddleware
from app.db import SessionLocal
from app.models import AdminAudit
from app.security import read_session_token

log = logging.getLogger(__name__)


class AdminAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.method != "POST" or not request.url.path.startswith("/admin"):
            return response
        identity = read_session_token(request.cookies.get("session", "")) or {}
        actor = getattr(request.state, "admin_actor", None) or identity.get("email") or "anonymous"
        factory = getattr(request.app.state, "audit_session_factory", SessionLocal)
        try:
            with factory() as db:
                # No request bodies, query strings, passwords or linking codes are recorded.
                db.add(AdminAudit(actor=actor[:200], action=request.method,
                                  target=request.url.path[:300], status=response.status_code))
                db.commit()
        except Exception:
            log.error("Could not persist administrative audit record")
        return response
