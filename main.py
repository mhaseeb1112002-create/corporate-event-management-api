"""FastAPI routes for corporate events and registrations."""
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

import models  # Register ORM tables before creating them.
import services
from auth import create_token, current_user, secret_key, verify_password
from db import Base, engine, get_session
from schemas import EventCreate, EventRead, EventUpdate, RegistrationCreate, RegistrationRead, Token


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate configuration and create tables for this teaching project."""
    secret_key()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Corporate Event Management API", version="1.0.0", description="Manage company events and employee registrations.", lifespan=lifespan)
Session = Annotated[AsyncSession, Depends(get_session)]
Authorized = Annotated[str, Depends(current_user)]


@app.post("/token", response_model=Token, tags=["Authentication"], summary="Log in and obtain an access token", responses={401: {"description": "Invalid username or password"}})
async def login(session: Session, form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """Authenticate a provisioned account using OAuth2 password form fields."""
    user = await services.find_user(session, form.username)
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    return Token(access_token=create_token(user.username))


@app.post("/events", response_model=EventRead, status_code=201, tags=["Events"], summary="Create an event", responses={401: {"description": "Authentication required"}})
async def create_event(data: EventCreate, session: Session, user: Authorized):
    """Create an event. Requires a bearer token."""
    return await services.create_event(session, data)


@app.get("/events", response_model=list[EventRead], tags=["Events"], summary="List and filter events")
async def list_events(session: Session, skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100), title: str | None = Query(None, max_length=200), date: date | None = None):
    """List events with optional title, date, and pagination filters."""
    return await services.list_events(session, skip, limit, title, date)


@app.get("/events/{event_id}", response_model=EventRead, tags=["Events"], summary="Get one event", responses={404: {"description": "Event not found"}})
async def get_event(event_id: int, session: Session):
    """Fetch a single event by ID."""
    return await services.get_event(session, event_id)


@app.put("/events/{event_id}", response_model=EventRead, tags=["Events"], summary="Replace an event", responses={404: {"description": "Event not found"}, 409: {"description": "Capacity below registration count"}})
async def update_event(event_id: int, data: EventUpdate, session: Session, user: Authorized):
    """Replace all event fields; capacity cannot drop below current registrations."""
    return await services.update_event(session, event_id, data)


@app.delete("/events/{event_id}", status_code=204, tags=["Events"], summary="Delete an event", responses={404: {"description": "Event not found"}})
async def delete_event(event_id: int, session: Session, user: Authorized):
    """Delete an event and its registrations."""
    await services.delete_event(session, event_id)
    return Response(status_code=204)


@app.post("/events/{event_id}/registrations", response_model=RegistrationRead, status_code=201, tags=["Registrations"], summary="Register an employee", responses={404: {"description": "Event not found"}, 409: {"description": "Duplicate registration or event full"}})
async def register(event_id: int, data: RegistrationCreate, session: Session):
    """Register an employee, subject to uniqueness and capacity."""
    return await services.register(session, event_id, data)


@app.get("/events/{event_id}/registrations", response_model=list[RegistrationRead], tags=["Registrations"], summary="List event registrations", responses={404: {"description": "Event not found"}})
async def registrations(event_id: int, session: Session, skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    """Get a page of registrations for the event."""
    return await services.list_registrations(session, event_id, skip, limit)


@app.delete("/registrations/{registration_id}", status_code=204, tags=["Registrations"], summary="Cancel a registration", responses={404: {"description": "Registration not found"}})
async def cancel_registration(registration_id: int, session: Session):
    """Cancel a registration by ID."""
    await services.delete_registration(session, registration_id)
    return Response(status_code=204)
