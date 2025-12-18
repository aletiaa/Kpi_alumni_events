from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))

    # roles: student, alumni, guest   (admins come from CSV)
    role: Mapped[str] = mapped_column(String(20), default="guest", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reset_token: Mapped[str | None] = mapped_column(String(256), nullable=True)
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(200), default="KPI")
    start_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    capacity: Mapped[int] = mapped_column(Integer, default=100)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    registration_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)

class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uq_user_event"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
