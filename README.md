# Reservini

Reservini is a booking tool for small businesses such as barbers, tutors or therapists. The owner sets up services and opening hours, shares a public booking page, and clients pick a free time.

The app is available in English and Spanish, and supports any time zone and currency.

## Features

- Owner accounts with registration, login and logout.
- Business profile with a public address, time zone, currency and weekly opening hours. Hours are edited by dragging blocks on a weekly grid or by typing them as text.
- Services with a length and a price. Services can be edited, hidden or deleted.
- Public booking page with the next two weeks of free times, filters by day and time of day, and protection against double bookings.
- Confirmation email after booking and a reminder email on the morning of the booking.
- Owner dashboard with upcoming bookings and cancellation, which notifies the client by email.
- Free plan limited to 20 bookings a month and a Pro plan without a limit. Switching plans is a demo and takes no payment.
- Light and dark mode.

## Stack

- Python 3.14 and Flask
- SQLAlchemy with SQLite for development and PostgreSQL in production
- Flask-Login, Flask-WTF, Flask-Limiter and Flask-Babel
- Plain HTML and CSS, with two small JavaScript files for the hours editor and the booking filters
- pytest

## Run locally

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Set `SECRET_KEY` in `.env` to a long random value:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Start the server. The database is created on the first start:

```bash
flask run
```

The app runs at http://127.0.0.1:5000.

Emails are only sent when the `MAIL_*` settings in `.env` point to an SMTP server. Without them, the app logs that the email was skipped.

## Tests

```bash
python -m pytest
```

## Translations

Texts are written in English in the code and translated in `reservini/translations/es/LC_MESSAGES/messages.po`. After changing texts:

```bash
pybabel extract -F babel.cfg -k _l -o messages.pot .
pybabel update -i messages.pot -d reservini/translations
pybabel compile -d reservini/translations
```

## Reminders

`flask send-reminders` sends the reminder emails that are due. It can run more often than needed without sending the same reminder twice.

In production, Vercel calls `/tasks/send-reminders` once a day. The route only runs when the request carries the `CRON_SECRET` value.

## Deploy

The app runs on Vercel with a PostgreSQL database on Neon.

1. Import the repository in Vercel.
2. Connect a Neon database from the Storage tab, which adds `DATABASE_URL`.
3. Add these environment variables: `SECRET_KEY`, `CRON_SECRET`, `TRUST_PROXY=1` and, to send emails, the `MAIL_*` values.

The tables are created on the first start.

`vercel.json` sends every request to `api/index.py` and schedules the daily reminders.
