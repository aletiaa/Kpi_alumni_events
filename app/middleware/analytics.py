from __future__ import annotations

import hashlib
import time
import uuid
from datetime import datetime
from pathlib import PurePosixPath

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.db import SessionLocal
from app.models import PageView, UserActivity
from app.security import read_session_token

IGNORED_PREFIXES = (
    "/static",
    "/favicon",
    "/health",
    "/analytics/page-duration",
    "/api/",
)
IGNORED_SUFFIXES = (
    ".css",
    ".js",
    ".map",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".woff",
    ".woff2",
    ".ttf",
)
ANALYTICS_COOKIE = "analytics_session_id"


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Centralized HTTP analytics collector independent from route logic."""

    def __init__(self, app, session_cookie_name: str = "session"):
        super().__init__(app)
        self.session_cookie_name = session_cookie_name

    async def dispatch(self, request: Request, call_next):
        if self._should_ignore(request):
            return await call_next(request)

        started = time.perf_counter()
        opened_at = datetime.utcnow()
        user_id = self._get_user_id(request)
        session_id, should_set_cookie = self._get_session_id(request)

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        route = self._route_name(request)
        self._record_request(
            request=request,
            user_id=user_id,
            session_id=session_id,
            route=route,
            viewed_at=opened_at,
            status_code=response.status_code,
            request_duration_ms=duration_ms,
        )

        if should_set_cookie:
            response.set_cookie(
                ANALYTICS_COOKIE,
                session_id,
                httponly=False,
                samesite="lax",
                max_age=60 * 60 * 24 * 365,
            )
        return response

    def _should_ignore(self, request: Request) -> bool:
        path = request.url.path
        if request.method.upper() == "OPTIONS":
            return True
        if request.method.upper() not in {"GET", "HEAD"}:
            return True
        if any(path.startswith(prefix) for prefix in IGNORED_PREFIXES):
            return True
        suffix = PurePosixPath(path).suffix.lower()
        return suffix in IGNORED_SUFFIXES

    def _get_user_id(self, request: Request) -> int | None:
        token = request.cookies.get(self.session_cookie_name)
        if not token:
            return None
        data = read_session_token(token)
        user_id = data.get("user_id") if data else None
        return int(user_id) if user_id else None

    def _get_session_id(self, request: Request) -> tuple[str, bool]:
        auth_token = request.cookies.get(self.session_cookie_name)
        if auth_token:
            digest = hashlib.sha256(auth_token.encode("utf-8")).hexdigest()
            return f"auth:{digest[:32]}", False

        existing = request.cookies.get(ANALYTICS_COOKIE)
        if existing:
            return existing[:80], False
        return f"anon:{uuid.uuid4().hex}", True

    def _route_name(self, request: Request) -> str:
        route = request.scope.get("route")
        if route and getattr(route, "name", None):
            return str(route.name)
        return request.url.path

    def _session_factory(self, request: Request):
        return getattr(request.app.state, "analytics_session_factory", SessionLocal)

    def _record_request(
        self,
        request: Request,
        user_id: int | None,
        session_id: str,
        route: str,
        viewed_at: datetime,
        status_code: int,
        request_duration_ms: float,
    ) -> None:
        db_factory = self._session_factory(request)
        db = db_factory()
        try:
            page = request.url.path
            if request.url.query:
                page = f"{page}?{request.url.query}"
            page = page[:1000]

            db.add(
                PageView(
                    user_id=user_id,
                    session_id=session_id,
                    page=page,
                    route=route,
                    http_method=request.method.upper(),
                    viewed_at=viewed_at,
                    request_duration_ms=request_duration_ms,
                    ip_address=self._client_ip(request),
                    user_agent=request.headers.get("user-agent", "")[:500],
                    referrer=(request.headers.get("referer") or request.headers.get("referrer") or "")[:1000],
                    response_status_code=status_code,
                )
            )

            activity = db.query(UserActivity).filter(UserActivity.session_id == session_id).first()
            if activity:
                activity.user_id = activity.user_id or user_id
                activity.last_activity = viewed_at
                activity.total_requests = (activity.total_requests or 0) + 1
                activity.duration_seconds = max(
                    0,
                    int((activity.last_activity - activity.first_activity).total_seconds()),
                )
            else:
                db.add(
                    UserActivity(
                        user_id=user_id,
                        session_id=session_id,
                        first_activity=viewed_at,
                        last_activity=viewed_at,
                        duration_seconds=0,
                        total_requests=1,
                    )
                )
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()[:80]
        return (request.client.host if request.client else "")[:80]
