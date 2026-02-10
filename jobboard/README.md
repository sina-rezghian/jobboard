# JobBoard

A Django + PostgreSQL job board project with two roles (`employer`, `jobseeker`), custom user model, email/SMS activation demo, job search, applications workflow, dashboards, alerts, and recommendations.

## 1. What This Project Includes

- Role-based signup/login (`employer`, `jobseeker`)
- Custom `accounts.User` model (Phase 3 requirement)
- Session management + project-wide logging (Phase 3 requirement)
- Email account activation via tokenized link (Phase 4 requirement)
- SMS activation demo (bonus):
  - user requests code from activation page (`Send code`)
  - button shows `Pending...` while request is in-flight
  - each send generates a new 6-digit code
  - code is logged to `logs/sms_demo.log` and printed to terminal
- Employer features:
  - create/edit jobs (title, salary range, benefits, required skills, etc.)
  - view submitted applications
  - download resume file
  - schedule interview
  - reject application
- Job seeker features:
  - upload one latest resume
  - browse/search/filter jobs
  - apply to job
  - track application status
  - save jobs
  - create job alerts
  - view recommendation list based on profile/resume skills + education
- In-app notifications + demo email/SMS logs
- Seed command and script for realistic test/demo data

## 2. Professor Requirements Coverage (from PDF)

### Phase-based requirements

- Phase 1:
  - apps defined (`accounts`, `jobs`, `resumes`)
  - domain models and relations implemented
- Phase 2:
  - views, URLs, templates, forms implemented
  - test/demo data command implemented (`seed_demo_data`)
- Phase 3:
  - custom user model implemented
  - session management implemented
  - logging implemented across core flows
- Phase 4:
  - custom managers/querysets implemented
  - email verification implemented
  - template inheritance implemented (`base.html`)
  - reporting docs provided
- Bonus:
  - SMS verification demo implemented
  - tests implemented

### JobBoard topic requirements

- Employer side:
  - signup/login: implemented
  - define job with salary/benefits/skills: implemented
  - list/edit own jobs: implemented
  - view applications for job: implemented
  - download resumes: implemented
  - set interview date/time: implemented
  - reject resume/application: implemented
- Job seeker side:
  - signup/login: implemented
  - upload resume: implemented
  - job list/details: implemented
  - search by title/salary/skills: implemented
  - apply for specific job: implemented
  - track review result: implemented (`submitted/interview/rejected`)
- Bonus:
  - email/SMS notification for result changes: implemented
  - recommendation by education/skills: implemented

## 3. Clean Project Structure

The project now uses one canonical runtime root:

- `manage.py` (repo root)
- `jobboard/settings.py`
- `accounts/`, `jobs/`, `resumes/` (top-level apps)

A duplicate nested project tree was removed from active runtime paths and backed up to:

- `/home/srz2003/Documents/jobboard_legacy_backup_2026-02-10/`

## 4. Requirements

- Python 3.11+
- PostgreSQL 14+
- pip

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 5. Environment Variables

Set values in `.env`:

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=jobboard_db
DB_USER=job_user
DB_PASSWORD=YourStrongPassHere
DB_HOST=localhost
DB_PORT=5432
SMS_ACTIVATION_TTL_SECONDS=600
```

Optional:

- `DJANGO_DEBUG=1`
- `DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost`
- `SESSION_COOKIE_AGE=3600`

## 6. PostgreSQL Setup

See `POSTGRES_SETUP.md` for full instructions.

Critical note for tests:

- DB user should have `CREATEDB` privilege so Django can create `test_...` databases.

## 7. Run the Project

Apply migrations:

```bash
source .venv/bin/activate
set -a; source .env; set +a
python manage.py migrate
```

Create admin:

```bash
python manage.py createsuperuser
```

Run server:

```bash
python manage.py runserver
```

Open:

- `http://127.0.0.1:8000/`

## 8. Seed Demo Data

Fast population script:

```bash
scripts/insert_test_data.sh
```

Custom example:

```bash
scripts/insert_test_data.sh qa QATest123! 4 8 4 2
```

Generated credentials file:

- `logs/test_users_<prefix>.txt`

## 9. SMS Activation Flow (Current)

1. User registers (account remains inactive).
2. User opens `/accounts/sms-activate/`.
3. User enters username and clicks `Send code`.
4. Button switches to `Pending...` during request.
5. New code is generated and logged:
   - terminal output
   - `logs/sms_demo.log`
6. User enters code and activates account.

## 10. Logs and Demo Artifacts

- app log: `logs/jobboard.log`
- SMS demo log: `logs/sms_demo.log`
- SMS scoped logs: `logs/sms/*.jsonl`
- Email demo log: `logs/email_demo.log`
- Email outbox artifacts: `logs/email/` and `logs/email_outbox.txt`

## 11. Validation Commands

```bash
set -a; source .env; set +a
python manage.py check
python manage.py makemigrations --check --dry-run
```

If `manage.py test` fails with `permission denied to create database`, grant PostgreSQL `CREATEDB` to your DB user.

## 12. Key Apps

- `accounts`: authentication, role handling, activation, notifications
- `jobs`: job posting/search, applications, interview/reject flow, alerts, recommendations, dashboards
- `resumes`: resume upload/list

## 13. Security and Production Notes

For deployment, you must:

- set strong `DJANGO_SECRET_KEY`
- set `DJANGO_DEBUG=0`
- set explicit `DJANGO_ALLOWED_HOSTS`
- configure real email backend / SMTP
- replace demo SMS logger with real SMS provider integration
- configure static/media serving and HTTPS
