"""Application rules and async database operations."""
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models import Event, Registration, User
from schemas import EventCreate, EventUpdate, RegistrationCreate


async def get_event(session: AsyncSession, event_id: int, lock: bool = False) -> Event:
    """Find an event, optionally locking its row for capacity changes."""
    query = select(Event).where(Event.id == event_id)
    if lock:
        query = query.with_for_update()
    event = (await session.execute(query)).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


async def create_event(session: AsyncSession, data: EventCreate) -> Event:
    """Save a new event."""
    event = Event(**data.model_dump())
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def list_events(session: AsyncSession, skip: int, limit: int, title: str | None, event_date: date | None) -> list[Event]:
    """Return a stable, optionally filtered page of events."""
    query = select(Event).order_by(Event.id)
    if title:
        # Escaping wildcard characters makes search mean a literal substring.
        term = title.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Event.title.ilike(f"%{term}%", escape="\\"))
    if event_date:
        query = query.where(Event.date == event_date)
    return list((await session.scalars(query.offset(skip).limit(limit))).all())


async def update_event(session: AsyncSession, event_id: int, data: EventUpdate) -> Event:
    """Replace event fields, refusing a capacity below existing registrations."""
    event = await get_event(session, event_id, lock=True)
    count = await session.scalar(select(func.count()).select_from(Registration).where(Registration.event_id == event_id))
    if data.max_capacity < count:
        raise HTTPException(status_code=409, detail="Capacity cannot be below the current registration count")
    for key, value in data.model_dump().items():
        setattr(event, key, value)
    await session.commit()
    await session.refresh(event)
    return event


async def delete_event(session: AsyncSession, event_id: int) -> None:
    """Delete an event and its registrations."""
    event = await get_event(session, event_id, lock=True)
    # Explicit delete also works in SQLite tests, where FK enforcement varies.
    from sqlalchemy import delete
    await session.execute(delete(Registration).where(Registration.event_id == event_id))
    await session.delete(event)
    await session.commit()


async def register(session: AsyncSession, event_id: int, data: RegistrationCreate) -> Registration:
    """Register once, serializing capacity checks via the PostgreSQL event row lock."""
    event = await get_event(session, event_id, lock=True)
    existing = await session.scalar(select(Registration.id).where(Registration.event_id == event_id, Registration.employee_email == data.employee_email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Employee is already registered for this event")
    count = await session.scalar(select(func.count()).select_from(Registration).where(Registration.event_id == event_id))
    if count >= event.max_capacity:
        raise HTTPException(status_code=409, detail="Event is at capacity")
    registration = Registration(event_id=event_id, **data.model_dump())
    session.add(registration)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Registration conflicts with existing data") from exc
    await session.refresh(registration)
    return registration


async def list_registrations(session: AsyncSession, event_id: int, skip: int, limit: int) -> list[Registration]:
    """Return registrations for an existing event."""
    await get_event(session, event_id)
    query = select(Registration).where(Registration.event_id == event_id).order_by(Registration.id).offset(skip).limit(limit)
    return list((await session.scalars(query)).all())


async def delete_registration(session: AsyncSession, registration_id: int) -> None:
    """Cancel an existing registration."""
    registration = await session.get(Registration, registration_id)
    if registration is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    await session.delete(registration)
    await session.commit()


async def find_user(session: AsyncSession, username: str) -> User | None:
    """Find an account by exact username."""
    return await session.scalar(select(User).where(User.username == username))
