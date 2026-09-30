import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.errors import handle_http_error, handle_validation_error, handle_server_error
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
from .services.survey_catalog import seed_additional_surveys
from .services.kpi_import import import_loop, clean_saved_import_labels
from .routers.kpi_import import router as kpi_import_router
from .routers.translations import router as translations_router
from .routers.messages import router as messages_router
from .routers.engagement import router as engagement_router
from .routers.bots import router as bots_router
from .routers.telegram_subscriptions import router as telegram_subscriptions_router
from .config import TELEGRAM_ENABLED, SEED_DEMO_DATA
from .services.telegram_live import poll_loop
from .services.telegram_broadcasts import delivery_loop, status_label
from .services.telegram_bot_jobs import reply_loop


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
        clean_saved_import_labels(db)
        db.commit()
        if SEED_DEMO_DATA:
            seed_events_if_empty(db)
            seed_demo_content_if_empty(db)
        seed_additional_surveys(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap_database()
    task = None
    telegram_task = None
    delivery_task = None
    reply_task = None
    if TELEGRAM_ENABLED and not getattr(app.state, "disable_telegram", False):
        telegram_task = asyncio.create_task(poll_loop(SessionLocal))
        delivery_task = asyncio.create_task(delivery_loop(SessionLocal))
        reply_task = asyncio.create_task(reply_loop(SessionLocal))
    app.state.telegram_tasks = [t for t in (telegram_task, delivery_task, reply_task) if t is not None]
    if not getattr(app.state, "disable_kpi_import", False):
        task = asyncio.create_task(import_loop(SessionLocal))
    try:
        yield
    finally:
        if reply_task:
            reply_task.cancel()
            with suppress(asyncio.CancelledError):
                await reply_task
        if delivery_task:
            delivery_task.cancel()
            with suppress(asyncio.CancelledError):
                await delivery_task
        if telegram_task:
            telegram_task.cancel()
            with suppress(asyncio.CancelledError):
                await telegram_task
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


app = FastAPI(title="Платформа випускників КПІ", lifespan=lifespan)
app.add_exception_handler(StarletteHTTPException, handle_http_error)
app.add_exception_handler(RequestValidationError, handle_validation_error)
app.add_exception_handler(Exception, handle_server_error)
app.add_middleware(AnalyticsMiddleware)

templates = Jinja2Templates(directory="app/templates")
from app.services.localization import content_text
from app.services.localization import display_name, display_datetime
templates.env.globals.update(display_name=display_name, display_datetime=display_datetime)
templates.env.globals["content_text"] = content_text
templates.env.globals["telegram_status"] = status_label
app.state.templates = templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(platform.router)
app.include_router(web.router)
app.include_router(messages_router)
app.include_router(engagement_router)
app.include_router(bots_router)
app.include_router(telegram_subscriptions_router)
app.include_router(admin.router)
app.include_router(admin_events.router)
app.include_router(admin_platform.router)
app.include_router(password_reset.router)
app.include_router(analytics.router)
app.include_router(assistant_router)
app.include_router(iot_router)
app.include_router(kpi_import_router)
app.include_router(translations_router)
