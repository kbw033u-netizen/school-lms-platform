# Wazito Schools

A Python-based school website and learning management system demo for Wazito Schools.

## Features

- Public school landing page
- Role-based login for admin, teacher, learner, and parent
- Student, teacher, parent, and admin dashboard views
- Live classroom schedule and meeting cards
- Digital library with downloadable resources
- Billing and invoices with balance overview
- Support/contact form with WhatsApp number: 0721954896
- SQLite-backed sample data for demo purposes

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open:

- http://127.0.0.1:8000/
- Login with one of the demo accounts:
  - Admin: admin@school.com / admin123
  - Teacher: teacher@school.com / teacher123
  - Student: student@school.com / student123
  - Parent: parent@school.com / parent123

## Project structure

- `main.py` – application entrypoint with routes, DB setup, and seed data
- `templates/` – HTML pages
- `static/styles.css` – styling
- `school.db` – SQLite database created at runtime

## Notes

This demo showcases the Wazito Schools platform experience for online learning, fee management, and parent communication.
