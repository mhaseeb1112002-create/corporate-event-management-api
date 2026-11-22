"""API tests using an isolated async SQLite database, not production data."""
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-only-secret-key-at-least-32-characters"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from auth import hash_password
from db import Base, get_session
from main import app
from models import User


@pytest_asyncio.fixture
async def client():
    """Give every test a clean in-memory database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with sessions() as session:
        session.add(User(username="teacher", password_hash=hash_password("long-test-password")))
        await session.commit()

    async def override_session():
        async with sessions() as session:
            yield session
    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await engine.dispose()


EVENT = {"title": "Python Workshop", "description": "Hands-on training", "date": "2027-06-10", "location": "Room 1", "max_capacity": 2}


async def credentials(client):
    """Log in and return an Authorization header."""
    response = await client.post("/token", data={"username": "teacher", "password": "long-test-password"})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


@pytest.mark.asyncio
async def test_auth_and_crud(client):
    assert (await client.post('/events', json=EVENT)).status_code == 401
    assert (await client.post('/token', data={'username': 'teacher', 'password': 'wrong'})).status_code == 401
    assert (await client.get('/events')).status_code == 200
    headers = await credentials(client)
    response = await client.post('/events', json=EVENT, headers=headers)
    assert response.status_code == 201
    event_id = response.json()['id']
    assert (await client.get(f'/events/{event_id}')).json()['title'] == EVENT['title']
    changed = dict(EVENT, title='Advanced Python')
    assert (await client.put(f'/events/{event_id}', json=changed, headers=headers)).json()['title'] == changed['title']
    assert (await client.delete(f'/events/{event_id}', headers=headers)).status_code == 204
    assert (await client.get(f'/events/{event_id}')).status_code == 404
    assert (await client.delete(f'/events/{event_id}', headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_registration_rules_and_cancel(client):
    headers = await credentials(client)
    event_id = (await client.post('/events', json=EVENT, headers=headers)).json()['id']
    one = {'employee_name': 'Ali', 'employee_email': 'Ali@example.com'}
    two = {'employee_name': 'Sara', 'employee_email': 'sara@example.com'}
    three = {'employee_name': 'Omar', 'employee_email': 'omar@example.com'}
    assert (await client.post('/events/999/registrations', json=one)).status_code == 404
    first = await client.post(f'/events/{event_id}/registrations', json=one)
    assert first.status_code == 201
    assert (await client.post(f'/events/{event_id}/registrations', json=one)).status_code == 409
    assert (await client.post(f'/events/{event_id}/registrations', json=two)).status_code == 201
    assert (await client.post(f'/events/{event_id}/registrations', json=three)).status_code == 409
    assert len((await client.get(f'/events/{event_id}/registrations')).json()) == 2
    assert (await client.put(f'/events/{event_id}', json=dict(EVENT, max_capacity=1), headers=headers)).status_code == 409
    assert (await client.delete(f"/registrations/{first.json()['id']}")).status_code == 204
    assert (await client.delete(f"/registrations/{first.json()['id']}")).status_code == 404
    assert (await client.post(f'/events/{event_id}/registrations', json=three)).status_code == 201
    assert (await client.get('/events/999/registrations')).status_code == 404


@pytest.mark.asyncio
async def test_validation_filtering_pagination_and_docs(client):
    headers = await credentials(client)
    for invalid in [dict(EVENT, title='   '), dict(EVENT, date='not-a-date'), dict(EVENT, max_capacity=0), {'title': 'missing'}]:
        assert (await client.post('/events', json=invalid, headers=headers)).status_code == 422
    for title, day in [('Python Intro', '2027-06-10'), ('python Advanced', '2027-06-10'), ('Python Other', '2027-06-11'), ('SQL', '2027-06-10')]:
        assert (await client.post('/events', json=dict(EVENT, title=title, date=day), headers=headers)).status_code == 201
    response = await client.get('/events', params={'title': 'PYTHON', 'date': '2027-06-10', 'skip': 1, 'limit': 1})
    assert [event['title'] for event in response.json()] == ['python Advanced']
    assert (await client.get('/events', params={'skip': -1})).status_code == 422
    assert (await client.get('/events', params={'limit': 101})).status_code == 422
    assert (await client.post('/events/1/registrations', json={'employee_name': '', 'employee_email': 'bad'})).status_code == 422
    assert (await client.get('/docs')).status_code == 200
    spec = (await client.get('/openapi.json')).json()
    assert '/events/{event_id}/registrations' in spec['paths']
