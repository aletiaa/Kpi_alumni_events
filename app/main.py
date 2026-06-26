from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.middleware.analytics import AnalyticsMiddleware
from app.routers import password_reset

from .db import Base, SessionLocal, engine
from .routers import admin, admin_events, admin_platform, analytics, auth, platform, web
from .routers.assistant import router as assistant_router
from .routers.iot import router as iot_router
from .services.migrate import (
    ensure_alumni_profile_columns,
    ensure_analytics_tables,
    ensure_email_verified_column,
    ensure_event_time_columns,
    ensure_event_social_tables,
    ensure_iot_visits_table,
    ensure_news_image_columns,
    ensure_notifications_table,
    ensure_password_reset_columns,
    ensure_regular_profiles_are_public,
)
from .services.seeding import seed_demo_content_if_empty, seed_events_if_empty


def bootstrap_database():
    Base.metadata.create_all(bind=engine)

    ensure_email_verified_column(engine)
    ensure_event_time_columns(engine)
    ensure_password_reset_columns(engine)
    ensure_alumni_profile_columns(engine)
    ensure_iot_visits_table(engine)
    ensure_event_social_tables(engine)
    ensure_news_image_columns(engine)
    ensure_analytics_tables(engine)
    ensure_notifications_table(engine)
    ensure_regular_profiles_are_public(engine)

    db = SessionLocal()
    try:
        seed_events_if_empty(db)
        seed_demo_content_if_empty(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap_database()
    yield


app = FastAPI(title="Платформа випускників КПІ", lifespan=lifespan)
app.add_middleware(AnalyticsMiddleware)

templates = Jinja2Templates(directory="app/templates")
app.state.templates = templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(platform.router)
app.include_router(web.router)
app.include_router(admin.router)
app.include_router(admin_events.router)
app.include_router(admin_platform.router)
app.include_router(password_reset.router)
app.include_router(analytics.router)
app.include_router(assistant_router)
app.include_router(iot_router)
