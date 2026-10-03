# Wazito Schools

A Django-powered school portal demo, served through Tornado and managed locally with Honcho. It includes role-based demo login, dashboards, live Zoom classes, library resources, exam PDF uploads, billing with payments, and support tickets.

## Run locally

Use Python 3.12 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
honcho start
```

Honcho runs Django migrations, seeds the demo data, and starts the Django development server on http://127.0.0.1:8000.

Demo accounts:

- Admin: `admin@school.com` / `admin123`
- Teacher: `teacher@school.com` / `teacher123`
- Student: `student@school.com` / `student123`
- Parent: `parent@school.com` / `parent123`

## Project structure

- `config/` – Django settings, URL configuration, WSGI, and Tornado entrypoint
- `school/` – school data models, portal views, tests, and demo-data command
- `templates/` – Django templates for the school portal
- `static/styles.css` – site styling, served directly by Tornado
- `Procfile` – Honcho web process and local database initialization
- `db.sqlite3` – local database created at runtime

The default SQLite database and secret key are for local development only. Set a unique `DJANGO_SECRET_KEY`, disable `DJANGO_DEBUG`, and configure `DJANGO_ALLOWED_HOSTS` before deploying anywhere shared.

Run the checks with `python manage.py check` and `python manage.py test`.

## Live Zoom classes

Teachers and admins can start a live Zoom lesson from the Classes page. Set `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, and `ZOOM_CLIENT_SECRET` (Zoom Server-to-Server OAuth app) to create real meetings; without them, demo join links are generated.

## Payments

Invoices no longer track a separate fees balance. Parents and students can pay invoices from the Billing page (M-Pesa, card, or bank); each payment is recorded and the invoice status updates to `Partially Paid` or `Paid`.

## Exam uploads

Teachers and admins can upload exam PDFs on the Exams page. Uploaded files are stored under `media/exams/` and are downloadable by everyone.
