# AlumnixHub Deployment Guide

This guide describes how to run AlumnixHub outside the local development machine.

## 1. Prepare The Repository

```powershell
git clone https://github.com/aletiaa/Kpi_alumni_events.git
cd Kpi_alumni_events
```

Use the deployment branch that contains the latest AlumnixHub work:

```powershell
git checkout codex/deploy-alumnixhub-clean
```

## 2. Required Environment Variables

Set these in the hosting provider dashboard. Do not commit `.env`.

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
SECRET_KEY=change-this-to-a-long-random-secret
APP_BASE_URL=https://your-public-domain.example
EMAIL_ENABLED=false
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
EMAIL_FROM_EMAIL=
IOT_API_KEY=change-this-if-iot-api-is-used
```

For local development, SQLite is acceptable:

```env
DATABASE_URL=sqlite:///./dev.db
```

For production, PostgreSQL is recommended.

## 3. Render Deployment

1. Open Render and create a new Web Service from the GitHub repository.
2. Connect the branch `codex/deploy-alumnixhub-clean`.
3. Use the existing `render.yaml` when Render detects it.
4. If configuring manually:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

5. Create a PostgreSQL database.
6. Add `DATABASE_URL`, `SECRET_KEY`, and `APP_BASE_URL`.
7. Deploy the service.

The app runs startup migrations automatically. Demo accounts and events are disabled by default (`SEED_DEMO_DATA=false`). Do not enable demo seeding in production.

## 4. Admin Access

Admin users are configured through `admins.csv`.

Format:

```csv
email,password_hash,full_name
```

Keep this file private; it is excluded from Git. Each administrator needs a PBKDF2-SHA256 password hash, not a plaintext password. Existing local files can be migrated without changing passwords:

```powershell
py -3.11 -m scripts.hash_admin_passwords
```

Provision the migrated file through your host's secret-file facility and set `ADMINS_CSV_PATH` to its absolute path. Login fails closed when the file is absent or contains plaintext credentials. The migration requires an existing local CSV and does not create administrators.

Administrator credentials were previously tracked. Removing the file does not remove old Git history: rotate old administrator passwords and any API credentials previously shared or committed before public deployment.

## 5. Email

Email is required for production account verification. If `EMAIL_ENABLED=false`, newly registered users will not receive a verification link and will not be able to log in until email delivery is configured or an administrator verifies them directly in the database.

To enable real email, configure SMTP:

```env
EMAIL_ENABLED=true
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-user
SMTP_PASSWORD=your-password
EMAIL_FROM_EMAIL=no-reply@example.com
```

In-app notifications always work even if SMTP is disabled.

## 6. Analytics

Centralized analytics is collected automatically by middleware. No per-route tracking code is needed.

The admin can view:

- page views;
- sessions;
- signed-in vs anonymous activity;
- average page duration;
- popular pages;
- CSV export.

The accurate page duration endpoint uses browser `sendBeacon`.

## 7. Production Checklist

- Use PostgreSQL, not local SQLite.
- Set a strong `SECRET_KEY`.
- Set `APP_BASE_URL` to the public HTTPS URL.
- Keep `.env` out of Git.
- Keep `admins.csv`, databases and `backups/` out of Git.
- Run only one application worker when Telegram polling is enabled; multiple polling processes conflict.
- Keep the hosting process online for Telegram replies and scheduled jobs.
- Confirm admin email exists in `admins.csv`.
- Run `py -3.11 -m pytest -q` before deploying.
- Check `/analytics` after deployment to confirm middleware writes data.

## 8. Local Smoke Test

```powershell
py -3.11 -m pytest -q
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/events`
- `http://127.0.0.1:8000/news`
- `http://127.0.0.1:8000/alumni`
- `http://127.0.0.1:8000/analytics`
