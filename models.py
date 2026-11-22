"""Persistent event, registration, and account records."""
from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class Event(Base):
    """An event with a fixed capacity."""
    __tablename__ = "events"
    __table_args__ = (CheckConstraint("max_capacity > 0", name="ck_event_capacity"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text)
    date: Mapped[date] = mapped_column(Date, index=True)
    location: Mapped[str] = mapped_column(String(200))
    max_capacity: Mapped[int]


class Registration(Base):
    """One employee's registration for an event."""
    __tablename__ = "registrations"
    __table_args__ = (UniqueConstraint("event_id", "employee_email", name="uq_event_employee"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    employee_name: Mapped[str] = mapped_column(String(200))
    employee_email: Mapped[str] = mapped_column(String(254))


class User(Base):
    """A login account, storing only a password hash."""
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
