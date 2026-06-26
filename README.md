# AlumnixHub

AlumnixHub is a FastAPI platform for KPI alumni communication: events, news, alumni profiles, cohort chats, surveys, notifications, recommendations, and centralized analytics.

## Local Start

```powershell
cd D:\Alina\Codex\2026-06-25\d-o\work\Kpi_alumni_events
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000.

If port `8000` is blocked, run:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8011
```

## Environment Variables

Use `.env.example` as the template. For production, set these variables in the hosting panel instead of committing `.env`:

- `DATABASE_URL` - PostgreSQL URL for production, or SQLite for local development.
- `SECRET_KEY` - a long random secret.
- `APP_BASE_URL` - public site URL, for example `https://your-site.onrender.com`.
- `EMAIL_ENABLED`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM_EMAIL` - email delivery settings.

## Deploy To Render

1. Push this repository to GitHub.
2. In Render, create a new Web Service from the GitHub repository.
3. Render can detect `render.yaml`; otherwise use:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Create a PostgreSQL database on Render or another provider.
5. Add the production `DATABASE_URL` to the Web Service environment variables.
6. Set `SECRET_KEY` and `APP_BASE_URL`.
7. Deploy the service.

The application creates missing tables and seed data on startup, so a new database can start empty.

## Docker

```powershell
docker build -t alumnixhub .
docker run --env-file .env -p 8000:8000 alumnixhub
```

## Tests

```powershell
py -3.11 -m pytest -q
```
