# PostgreSQL Setup Manual

This project is configured to run only on PostgreSQL.

## 1) Install and start PostgreSQL

- Linux (systemd):
  - `sudo apt install postgresql postgresql-contrib`
  - `sudo systemctl enable --now postgresql`
- Windows:
  - Install PostgreSQL from the official installer and start the service.

## 2) Create database and user

Open `psql` as postgres admin and run:

```sql
CREATE DATABASE jobboard_db;
CREATE USER job_user WITH PASSWORD 'YourStrongPassHere';
ALTER ROLE job_user SET client_encoding TO 'utf8';
ALTER ROLE job_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE job_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE jobboard_db TO job_user;
ALTER USER job_user CREATEDB;
```

`CREATEDB` is needed for `manage.py test`, because Django creates a temporary test database.

## 3) Configure `.env`

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=jobboard_db
DB_USER=job_user
DB_PASSWORD=YourStrongPassHere
DB_HOST=localhost
DB_PORT=5432
```

## 4) Run migrations

```bash
.venv/bin/python manage.py migrate
```

## 5) Seed demo/test data

```bash
scripts/insert_test_data.sh qa QATest123! 4 8 4 2
```

Credentials will be written to:

```text
logs/test_users_qa.txt
```

## 6) Run server

```bash
.venv/bin/python manage.py runserver
```
