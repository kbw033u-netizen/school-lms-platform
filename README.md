# Wazito Schools

A Django-powered school portal demo for school administrators, teachers, students, and parents. Django handles application logic and templates; WhiteNoise serves static files, and Gunicorn runs the Django WSGI application in production.

## Features

- Role-based sign-in and dashboards for admins, teachers, students, and parents.
- Class schedules and live lessons. Zoom Server-to-Server OAuth credentials enable real Zoom meetings; without them, the app creates demo join links.
- A school library for learning materials and an exams area for PDF uploads.
- Student invoices and payment records, with optional M-Pesa STK Push, PayPal Checkout, and Stripe Checkout integrations.
- Support tickets and contact forms.

Payment and Zoom integrations run in demo mode when their credentials are not configured. Do not treat locally recorded demo payments or sample accounts as production data.

## Run locally

Requirements: Python 3.12 or newer. SQLite is used by default, so a local database server is not required.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
set -a
source .env
set +a
python manage.py migrate --noinput
python manage.py seed_school_data
python manage.py runserver 127.0.0.1:8000
```

The portal is available at <http://127.0.0.1:8000>. The `.env` file is sourced into the current shell because Django does not load it automatically. Keep local secrets in `.env`; do not commit credentials.

`seed_school_data` creates sample accounts, library materials, classes, and invoices. It is safe to rerun for the existing sample records; it does not reset passwords on accounts that already exist.

## Demo accounts

These credentials are for local development only. Never use them on a public deployment.

Demo accounts:

- Admin: `admin@school.com` / `admin123`
- Teacher: `teacher@school.com` / `teacher123`
- Student: `student@school.com` / `student123`
- Parent: `parent@school.com` / `parent123`

## Configuration

The application reads settings from environment variables. Add optional integration settings to `.env` as needed.

| Variable | Purpose | Default or behavior |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Django signing and security key | The built-in fallback is for local development only; set a private value elsewhere. |
| `DJANGO_DEBUG` | Enable Django debug mode | `false` in settings; `.env.example` sets it to `true` for local development. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hostnames | `localhost,127.0.0.1,testserver` |
| `DATABASE_URL` | Database connection URL | If omitted, SQLite is used. |
| `SCHOOL_DB_PATH` | SQLite database file path | `db.sqlite3` in the project directory; ignored when `DATABASE_URL` is set. |
| `SCHOOL_MEDIA_ROOT` | Directory for uploaded files | `media/` in the project directory. |
| `PORT` | Web server port | `8000` locally; Render provides the production port. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins | Empty; use full origins such as `https://portal.example.com`. |
| `SECURE_SSL_REDIRECT` | Redirect HTTP requests to HTTPS | `false` |
| `SECURE_HSTS_SECONDS` | HSTS duration in seconds | `0` |

Render supplies `DATABASE_URL`, `PORT`, and `RENDER_EXTERNAL_HOSTNAME`. Its Blueprint configures the public bind address, persistent media directory, HTTPS redirect, and HSTS. Review host and security settings before using another hosting platform.

### Optional integrations

- **Zoom:** Set `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, and `ZOOM_CLIENT_SECRET` for a Zoom Server-to-Server OAuth app.
- **M-Pesa:** Set `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_SHORTCODE`, and `MPESA_PASSKEY`. `MPESA_ENV` defaults to `sandbox`; use `production` only with live Daraja credentials. `MPESA_CALLBACK_URL` can override the callback URL.
- **PayPal:** Set `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`. `PAYPAL_ENV` defaults to `sandbox`; use `live` for the live API.
- **Stripe:** Set `STRIPE_SECRET_KEY` to enable Stripe Checkout. Use a Stripe test key while testing.

Without payment-provider credentials, payment flows record local demo payments instead of contacting the providers.

## Development commands

Run Django's configuration checks and test suite with:

```bash
python manage.py check
python manage.py test
```

To create the first administrator on a deployed instance, run `python manage.py create_portal_admin`. It prompts for administrator details and a password of at least 12 characters. Do not seed demo accounts on a public deployment.

## Project structure

- `config/` – Django settings, URL configuration, and WSGI application.
- `school/` – models, views, payment and Zoom integrations, tests, and management commands.
- `templates/` – Django templates for portal pages.
- `static/` – CSS and browser-side JavaScript collected and served by WhiteNoise.
- `library/` – bundled library resources.
- `render.yaml` – Render Blueprint for the web service, PostgreSQL database, and upload disk.

## Deploy on Render

The Blueprint in `render.yaml` creates a paid web service, PostgreSQL database, and persistent disk for uploads. Review current Render pricing before applying it. Deploy through <https://render.com/deploy?repo=https://github.com/kbw033u-netizen/school-lms-platform> and apply the Blueprint. The build installs dependencies and collects static files, the pre-deploy step runs migrations, and Gunicorn serves Django on Render's assigned port. Render checks `/healthz`, which verifies that the app can reach its database. Uploaded media is stored on the persistent disk. Demo accounts are not seeded in production.

After the first deploy, open the service Shell and run `python manage.py create_portal_admin`, then sign in and create staff accounts. Add Zoom or payment-provider credentials as Render environment variables if live integrations are required. Exam PDFs are stored under `media/exams/`.
