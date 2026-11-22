import os, asyncio, tempfile
from pathlib import Path
from pgserver import initdb, pg_ctl
p=Path(tempfile.mkdtemp(prefix='event-pg-'))
initdb(['--username=postgres','--auth=trust'],pgdata=p)
pg_ctl(['-w','-o',"-h 127.0.0.1 -p 55472 -c unix_socket_directories=''",'-l',str(p/'server.log'),'start'],pgdata=p)
os.environ['DATABASE_URL']='postgresql+asyncpg://postgres@127.0.0.1:55472/postgres'
os.environ['JWT_SECRET']='temporary-integration-test-secret-at-least-32-characters'
try:
 from httpx import AsyncClient, ASGITransport
 from main import app
 from db import SessionLocal
 from models import User
 from auth import hash_password
 async def run():
  async with app.router.lifespan_context(app):
   async with SessionLocal() as s:
    s.add(User(username='tester',password_hash=hash_password('test-password-long')))
    await s.commit()
   async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test',trust_env=False) as c:
    async def req(label, method, path, expected, **kwargs):
     response=await c.request(method,path,**kwargs)
     assert response.status_code==expected,(label,response.status_code,response.text)
     print(label,response.status_code,'PASS',flush=True)
     return response
    pld={'title':'Python Workshop','description':'Training','date':'2027-06-10','location':'Room 1','max_capacity':1}
    await req('Unauthenticated create','POST','/events',401,json=pld)
    token=(await req('Login','POST','/token',200,data={'username':'tester','password':'test-password-long'})).json()['access_token']
    h={'Authorization':'Bearer '+token}
    eid=(await req('Create','POST','/events',201,json=pld,headers=h)).json()['id']
    await req('List and filter','GET','/events?title=python&date=2027-06-10&skip=0&limit=10',200)
    await req('Get event','GET',f'/events/{eid}',200)
    await req('Update event','PUT',f'/events/{eid}',200,json=dict(pld,location='Room 2'),headers=h)
    pair=await asyncio.gather(c.post(f'/events/{eid}/registrations',json={'employee_name':'Ali','employee_email':'ali@example.com'}),c.post(f'/events/{eid}/registrations',json={'employee_name':'Sara','employee_email':'sara@example.com'}))
    statuses=sorted(r.status_code for r in pair)
    assert statuses == [201,409], [(r.status_code,r.text) for r in pair]
    print('Concurrent last-seat registrations:',statuses,'PASS',flush=True)
    winner=next(r.json() for r in pair if r.status_code==201)
    await req('Duplicate rejected','POST',f'/events/{eid}/registrations',409,json={'employee_name':winner['employee_name'],'employee_email':winner['employee_email']})
    await req('List registrations','GET',f'/events/{eid}/registrations',200)
    await req('Invalid registration','POST',f'/events/{eid}/registrations',422,json={'employee_name':'','employee_email':'bad'})
    await req('Missing event','POST','/events/9999/registrations',404,json={'employee_name':'Ali','employee_email':'ali@example.com'})
    await req('Cancel','DELETE',f"/registrations/{winner['id']}",204)
    await req('Delete event','DELETE',f'/events/{eid}',204,headers=h)
    await req('Missing deleted event','GET',f'/events/{eid}',404)
    await req('Swagger','GET','/docs',200)
    print('All PostgreSQL integration checks passed.',flush=True)
 asyncio.run(run())
finally:
 pg_ctl(['-w','stop'],pgdata=p)
