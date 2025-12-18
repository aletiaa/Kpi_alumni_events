from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import password_reset

from .db import Base, engine, SessionLocal
from .routers import auth, web, admin, admin_events
from .services.migrate import ensure_email_verified_column, ensure_event_time_columns, ensure_password_reset_columns
from .services.seeding import seed_events_if_empty
from .routers.assistant import router as assistant_router
from app.routers.iot import router as iot_router

app = FastAPI(title="KPI Events Dashboard")


templates = Jinja2Templates(directory="app/templates")
app.state.templates = templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(web.router)
app.include_router(admin.router)
app.include_router(admin_events.router)
app.include_router(password_reset.router)
app.include_router(assistant_router)
app.include_router(iot_router)

@app.on_event("startup")
def on_startup():
    # 1) create tables
    Base.metadata.create_all(bind=engine)

    # 2) migrations first (so models can query safely)
    ensure_email_verified_column(engine)
    ensure_event_time_columns(engine)
    ensure_password_reset_columns(engine)

    # 3) seed after migrations
    db = SessionLocal()
    try:
        seed_events_if_empty(db)
    finally:
        db.close()
