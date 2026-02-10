# Test Data Insert Guide

This project already includes a Django seed command (`seed_demo_data`).  
Use this helper script to insert demo employers, job seekers, jobs, and applications quickly:

```bash
scripts/insert_test_data.sh
```

The script uses PostgreSQL by default (`DB_ENGINE=django.db.backends.postgresql`).
For full DB setup, see `POSTGRES_SETUP.md`.

Default output:
- `5` employers
- `10` job seekers
- `4` jobs per employer
- `3` applications per seeker
- all accounts use password: `DemoPass123!`

Credentials are written to:

```text
logs/test_users_demo.txt
```

## Custom insert

```bash
scripts/insert_test_data.sh <prefix> <password> <employers> <jobseekers> <jobs_per_employer> <applications_per_seeker>
```

Example:

```bash
scripts/insert_test_data.sh qa QATest123! 3 6 4 2
```

If you need to override DB settings explicitly:

```bash
DB_ENGINE=django.db.backends.postgresql scripts/insert_test_data.sh qa QATest123! 3 6 4 2
```

This creates:
- employers: `qa_emp_1 ... qa_emp_3`
- job seekers: `qa_seeker_1 ... qa_seeker_6`
- all with password: `QATest123!`

and writes them to:

```text
logs/test_users_qa.txt
```

## Login URL

- `/accounts/login/`
