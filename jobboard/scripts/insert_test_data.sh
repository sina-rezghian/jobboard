#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/insert_test_data.sh [prefix] [password] [employers] [jobseekers] [jobs_per_employer] [applications_per_seeker]
#
# Example:
#   scripts/insert_test_data.sh demo DemoPass123! 5 10 4 3

PREFIX="${1:-demo}"
PASSWORD="${2:-DemoPass123!}"
EMPLOYERS="${3:-5}"
JOBSEEKERS="${4:-10}"
JOBS_PER_EMPLOYER="${5:-4}"
APPLICATIONS_PER_SEEKER="${6:-3}"

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python executable not found at ${PYTHON_BIN}."
  echo "Set PYTHON_BIN explicitly, e.g. PYTHON_BIN=python3 scripts/insert_test_data.sh"
  exit 1
fi

# Default to PostgreSQL.
export DB_ENGINE="${DB_ENGINE:-django.db.backends.postgresql}"

echo "Running migrations (DB_ENGINE=${DB_ENGINE})..."
"${PYTHON_BIN}" manage.py migrate

echo "Seeding demo data..."
"${PYTHON_BIN}" manage.py seed_demo_data \
  --prefix "${PREFIX}" \
  --employers "${EMPLOYERS}" \
  --jobseekers "${JOBSEEKERS}" \
  --jobs-per-employer "${JOBS_PER_EMPLOYER}" \
  --applications-per-seeker "${APPLICATIONS_PER_SEEKER}" \
  --password "${PASSWORD}" \
  --wipe

OUT_FILE="logs/test_users_${PREFIX}.txt"
mkdir -p logs
{
  echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
  echo "Prefix: ${PREFIX}"
  echo "Password (all users): ${PASSWORD}"
  echo
  echo "[Employer Users]"
  for ((i=1; i<=EMPLOYERS; i++)); do
    echo "${PREFIX}_emp_${i} / ${PASSWORD}"
  done
  echo
  echo "[Job Seeker Users]"
  for ((i=1; i<=JOBSEEKERS; i++)); do
    echo "${PREFIX}_seeker_${i} / ${PASSWORD}"
  done
} > "${OUT_FILE}"

echo "Done."
echo "Credentials written to: ${OUT_FILE}"
echo "Employers: ${EMPLOYERS} | Job seekers: ${JOBSEEKERS} | Jobs per employer: ${JOBS_PER_EMPLOYER}"
