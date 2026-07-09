from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    callsign: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    platoon: Mapped[str] = mapped_column(String(10), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="operator")
    totp_secret: Mapped[str] = mapped_column(String(32), nullable=True, default=None)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platoon: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    callsign: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    month: Mapped[str] = mapped_column(String(3), nullable=False)

    equipment_ok: Mapped[str] = mapped_column(String(3), nullable=False)
    skills_ok: Mapped[str] = mapped_column(String(3), nullable=False)
    total_hf_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    j0g_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gst_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    other_hf_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_mars_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    submission_source: Mapped[str] = mapped_column(String(20), nullable=False, default="paste")
    duplicate_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    submitted_by: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
