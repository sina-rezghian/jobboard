# Run (Windows CMD)

## 1) Go to project root
cd /d E:\Dj-pro\jobboard-main\job-seeker\jobboard

## 2) Create & activate venv
python -m venv .venv
.venv\Scripts\activate

## 3) Install deps
pip install -r requirements.txt

## 4) Set DB env (replace password)
set DB_NAME=jobboard_db
set DB_USER=job_user
set DB_PASSWORD=YOUR_PASSWORD
set DB_HOST=127.0.0.1
set DB_PORT=5432

## 5) Migrate and run
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

Open: http://127.0.0.1:8000/
