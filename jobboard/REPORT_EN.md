# Final Academic Report - JobBoard Project

## Report Information

- Student Name: **Sina Rezghian**
- Project Title: **Design and Implementation of the JobBoard Recruitment Platform**
- Course: **Web Programming**
- Technology Stack: **Django 5.x, PostgreSQL, Bootstrap 5**

---

## Abstract

In this project, I designed and implemented a web-based recruitment platform with two primary roles: employer and job seeker. The system covers the core hiring lifecycle from job posting to application submission, resume review, interview scheduling, and decision updates. The architecture is modular, built around three main applications: `accounts`, `jobs`, and `resumes`. In addition to core requirements, I implemented extended features such as in-app notifications, job alerts, skill recommendations, job recommendations, email activation, and demo SMS activation. This report provides the final technical and academic documentation of the project, including data model design, key methods, implemented features, development challenges, and complete setup instructions.

**Keywords:** Django, PostgreSQL, Job Board, Authentication, Recommendation, Notification

---

## 1) Introduction

The objective of this project was to build a complete two-sided recruitment platform where:

- employers can create and manage job opportunities,
- job seekers can search jobs and submit applications,
- application status can be tracked through a clear workflow.

Throughout implementation, I focused on three priorities:

- strict requirement coverage,
- maintainable architecture,
- practical user experience.

---

## 2) Project Objectives

The main implementation goals were:

1. Full employer/job seeker workflow implementation
2. Coverage of all required phases of the course project
3. Accurate and practical search/filter logic
4. End-to-end application lifecycle support
5. Advanced features (alerts, recommendations, notifications)
6. Reliable PostgreSQL-based setup and reproducible test data process

---

## 3) System Architecture

Final project structure:

- `jobboard/`: core settings, root URLs, global configuration
- `accounts/`: authentication, roles, activation, notifications
- `jobs/`: job lifecycle, search, applications, dashboards, alerts
- `resumes/`: resume upload and management
- `templates/`, `static/`: presentation layer
- `scripts/`: setup and test data scripts

This modular structure improves maintainability and clear separation of concerns.

---

## 4) Data Model and Relationships

### 4.1 `accounts` app

- `User` (inherits from `AbstractUser`)
  - extra fields: `email(unique)`, `role`, `is_email_verified`, `sms_activation_code`, `sms_activation_sent_at`
- `EmployerProfile` (`OneToOne` with `User`)
- `JobSeekerProfile` (`OneToOne` with `User`)
- `Notification` (`ForeignKey` to `User`)

### 4.2 `jobs` app

- `Job` (`ForeignKey` to `EmployerProfile`)
- `JobApplication` (connects `Job` and `JobSeekerProfile`)
- `JobApplicationEvent` (application timeline)
- `ApplicationNote` (internal employer notes)
- `SavedJob` (bookmarked jobs)
- `JobAlert` (saved search criteria)
- `JobAlertMatch` (alert-to-job matched records)

### 4.3 `resumes` app

- `Resume` (`ForeignKey` to `JobSeekerProfile`, file + metadata)

---

## 5) Technical Methods and Implementation

## 5.1 Manager / QuerySet layer

### `JobQuerySet` and `JobManager`

- `recent()`
- `for_employer(employer)`
- `search(q, min_salary, max_salary, skills, company, job_type, experience_level, cover_letter_required)`

Purpose:

- centralized query logic,
- reusable and consistent filtering behavior,
- cleaner view layer.

### `JobApplicationQuerySet` and `JobApplicationManager`

- `submitted()`
- `interviews()`
- `rejected()`
- `for_job(job)`
- `for_jobseeker(jobseeker)`

Purpose:

- status-driven data access,
- simpler dashboard/report queries.

## 5.2 Key methods in `jobs.views`

- `_normalize_space()`, `_safe_int()` for input normalization
- `_popular_skill_suggestions()`, `_skill_suggestions_by_prefix()` for dynamic skill suggestions
- `_apply_skill_suggestions()` for application form assistance
- `_last_7_days_application_series()` for employer weekly chart data
- `job_list()` for advanced search/filter/sort pipeline
- `apply_job()` for application submission flow
- `schedule_interview()` for date/time interview assignment
- `job_alerts()` and `alert_inbox()` for alert lifecycle
- `dashboard()` for role-based metrics views

## 5.3 Key methods in `accounts.views`

- `register_employer()`, `register_jobseeker()`
- `activate_account()` (email-based activation)
- `sms_send_code()`, `sms_activate()` (demo SMS activation flow)
- `_send_demo_sms_activation()` for secure code generation and TTL flow
- `notifications_list()`, `notification_mark_read()`, `notifications_mark_all_read()`

---

## 6) Implemented Features

## 6.1 Public features

- landing page with latest jobs
- clickable featured companies linked to filtered job search
- fast keyword/skills search entry point

## 6.2 Job seeker features

- registration, login, account activation
- resume upload
- job browsing and detailed search filters:
  - keyword
  - company
  - city
  - salary range
  - skills
  - contract/job type
  - experience level
  - cover letter requirement
  - sorting options
- skills autocomplete in search
- application submission
- status tracking (Submitted / Interview / Rejected)
- saved jobs
- job alerts + alert inbox
- in-app notifications

## 6.3 Employer features

- registration, login, activation
- create/edit jobs
- skills recommendation in posting/edit forms
- applications overview
- application detail and internal notes
- interview scheduling with date and time
- reject flow
- dashboard with last-7-days daily applications chart

## 6.4 Notification layer

- in-app notifications
- demo email notifications
- demo SMS notifications

---

## 7) Hypothetical Past Development Challenges and Resolution Approach

The following are realistic hypothetical issues that could have occurred during earlier development stages, along with how I handled them in implementation:

### Challenge 1: Over-broad search behavior for short tokens

- Scenario: early search behavior could return too many irrelevant results for short terms.
- Resolution: refined model-level search logic to constrain short-token matching.
- Outcome: more accurate and user-expected search results.

### Challenge 2: Inconsistent skill entry UX

- Scenario: manual skill typing could be slow and inconsistent across forms.
- Resolution: implemented dynamic skill-suggestion API and autocomplete integration.
- Outcome: faster form completion and cleaner skill data.

### Challenge 3: Alert relevance visibility gaps

- Scenario: users might not receive meaningful alert inbox items right after creating alerts.
- Resolution: added backfill matching on alert creation.
- Outcome: alert inbox becomes useful immediately after alert setup.

### Challenge 4: Employer chart rendering gaps

- Scenario: weekly chart could appear empty due to missing or unsynchronized data handling.
- Resolution: implemented explicit 7-day daily aggregation with fallback rendering.
- Outcome: stable chart behavior with or without available data.

### Challenge 5: SMS activation usability friction

- Scenario: activation flow might be unclear without explicit send-code action.
- Resolution: introduced dedicated send-code action, pending UI state, TTL-safe code validation, and post-activation login.
- Outcome: clearer activation flow and improved completion rate.

---

## 8) Project Setup Guide

## 8.1 Prerequisites

- Python 3.11+
- PostgreSQL 14+
- pip

## 8.2 Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 8.3 PostgreSQL initialization

Run in `psql`:

```sql
CREATE DATABASE jobboard_db;
CREATE USER job_user WITH PASSWORD 'YourStrongPassHere';
ALTER ROLE job_user SET client_encoding TO 'utf8';
ALTER ROLE job_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE job_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE jobboard_db TO job_user;
ALTER USER job_user CREATEDB;
```

## 8.4 Environment configuration (`.env`)

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=jobboard_db
DB_USER=job_user
DB_PASSWORD=YourStrongPassHere
DB_HOST=localhost
DB_PORT=5432
SMS_ACTIVATION_TTL_SECONDS=600
```

## 8.5 Migrations and run

```bash
source .venv/bin/activate
set -a; source .env; set +a
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Access URL:

- `http://127.0.0.1:8000/`

---

## 9) Test Data Import Guide

Default command:

```bash
scripts/insert_test_data.sh
```

Custom command:

```bash
scripts/insert_test_data.sh qa QATest123! 4 8 4 2
```

Arguments:

1. username prefix
2. shared password
3. number of employers
4. number of job seekers
5. jobs per employer
6. applications per seeker

Generated credentials file:

- `logs/test_users_<prefix>.txt`

---

## 10) Validation Commands

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python -m compileall accounts jobs resumes jobboard
```

If `python manage.py test` fails with test database creation permission error, grant `CREATEDB` privilege to the PostgreSQL user.

---

## 11) Conclusion

This project delivers a complete academic job board system with a clear business workflow, maintainable architecture, and practical user-facing features. From data model design to role-based dashboards and setup reproducibility, the final implementation is suitable for formal presentation and extensible for future iterations.
