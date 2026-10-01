# Wazito Schools

A Django-powered school portal demo, served through Tornado and managed locally with Honcho. It includes role-based demo login, dashboards, classes, library resources, billing, and support tickets.

## Run locally

Use Python 3.12 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
honcho start
```

Honcho runs Django migrations, seeds the demo data, and starts Tornado on http://127.0.0.1:8000.

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
