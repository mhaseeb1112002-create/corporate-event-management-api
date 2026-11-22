"""Capture real Swagger UI responses against a disposable SQLite database."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./swagger_demo.db'
os.environ['JWT_SECRET'] = 'temporary-demo-key-not-used-outside-this-job'
server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'])
try:
    client = httpx.Client(base_url='http://127.0.0.1:8000', trust_env=False)
    for attempt in range(100):
        try:
            if client.get('/openapi.json').status_code == 200:
                break
        except httpx.ConnectError:
            time.sleep(.2)
    else:
        raise RuntimeError('API did not start')
    import asyncio
    from auth import hash_password
    from db import SessionLocal
    from models import User
    async def seed():
        async with SessionLocal() as session:
            session.add(User(username='demo-user', password_hash=hash_password('temporary-demo-password')))
            await session.commit()
    asyncio.run(seed())
    output = Path('swagger-screenshots')
    output.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
        page.goto('http://127.0.0.1:8000/docs', wait_until='networkidle')
        page.get_by_role('button', name='Authorize', exact=True).first.click()
        dialog = page.locator('.auth-container')
        dialog.locator('input').nth(0).fill('demo-user')
        dialog.locator('input').nth(1).fill('temporary-demo-password')
        page.locator('.modal-ux').get_by_role('button', name='Authorize', exact=True).click()
        page.get_by_role('button', name='Close', exact=True).last.click()

        def execute(method, path, name, params=None, body=None, expected=200):
            op = page.locator(f'.opblock-{method.lower()}').filter(has=page.locator(f'.opblock-summary-path[data-path="{path}"]'))
            op.locator('.opblock-summary').click()
            op.get_by_role('button', name='Try it out').click()
            if params:
                for param, value in params.items():
                    op.locator(f'[data-param-name="{param}"]').locator('input').fill(str(value))
            if body is not None:
                op.locator('textarea').fill(json.dumps(body, indent=2))
            op.get_by_role('button', name='Execute', exact=True).click()
            op.locator('.live-responses-table .response-col_status').get_by_text(str(expected), exact=True).first.wait_for(timeout=20000)
            # Hide the temporary request token from the screenshot.
            op.locator('.curl').evaluate("el => { el.style.visibility = 'hidden'; }")
            op.scroll_into_view_if_needed()
            op.screenshot(path=str(output / f'{name}.png'), timeout=20000)
            op.locator('.opblock-summary').click()
        event={'title':'Python Workshop','description':'Learn FastAPI','date':'2027-06-10','location':'Room 1','max_capacity':2}
        registration={'employee_name':'Demo Employee','employee_email':'demo@example.com'}
        execute('post','/events','01-create-event',body=event,expected=201)
        execute('get','/events','02-list-events')
        execute('get','/events/{event_id}','03-get-event',params={'event_id':1})
        execute('put','/events/{event_id}','04-update-event',params={'event_id':1},body=dict(event, location='Room 2'))
        execute('post','/events/{event_id}/registrations','05-register',params={'event_id':1},body=registration,expected=201)
        execute('get','/events/{event_id}/registrations','06-list-registrations',params={'event_id':1})
        execute('delete','/registrations/{registration_id}','07-cancel-registration',params={'registration_id':1},expected=204)
        execute('delete','/events/{event_id}','08-delete-event',params={'event_id':1},expected=204)
        browser.close()
    print('Captured eight Swagger request and response screenshots.')
finally:
    server.terminate()
    server.wait(timeout=10)
