# Demo recording guide

Record your own narration and only explain features you understand. Use PostgreSQL and Swagger at `/docs`. The assignment requires a personal demonstration of all implemented endpoints; this guide is not a substitute for the video.

1. Introduce the API and explain its purpose.
2. Show the folder structure. Explain `db.py`, `models.py`, `schemas.py`, `services.py`, `main.py`, `auth.py`, and `create_user.py`.
3. Show the PostgreSQL database and describe how SQLAlchemy async sessions read and write data. Do not reveal passwords or tokens.
4. Show `/docs`, log in through **Authorize**, and explain why a hash and JWT are used.
5. Demonstrate `POST /events`, `GET /events` (including filters and pagination), `GET /events/{id}`, and `PUT /events/{id}`.
6. Register an employee, list registrations, demonstrate a duplicate (409), fill the event and demonstrate capacity (409), and demonstrate an invalid request (422) and missing event (404).
7. Cancel a registration with `DELETE /registrations/{id}`, then delete the event with `DELETE /events/{id}`. Show how deletion handles registrations.
8. Run `python -m pytest -q` and explain what the tests cover and their SQLite limitation. Show PostgreSQL working separately.
9. Capture Swagger screenshots of successful requests and responses for every endpoint. Keep your token out of shared images.
10. Explain transaction locking, the unique constraint, and one tradeoff or limitation in your own words.
