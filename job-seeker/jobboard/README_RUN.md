# JobBoard (Phase 3 & 4) - Ready Project

## Quick start (Windows CMD)
1) Create and activate venv:
   python -m venv .venv
   .venv\Scripts\activate

2) Install deps:
   pip install -r requirements.txt

3) Configure PostgreSQL in jobboard/settings.py (DATABASES)

4) Migrate + create admin user:
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser

5) Run:
   python manage.py runserver

Open: http://127.0.0.1:8000/


### SMS Demo Output
Demo SMS messages are stored in `logs/sms_demo.log`.
