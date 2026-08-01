#!/usr/bin/env bash
set -Eeuo pipefail

development_database="${POSTGRES_DEV_DB:-study_for_job_dev}"

if [ "${development_database}" = "${POSTGRES_DB}" ]; then
  echo "POSTGRES_DEV_DB must differ from POSTGRES_DB" >&2
  exit 1
fi

psql --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" --set=development_database="${development_database}" --set=ON_ERROR_STOP=1 <<-'EOSQL'
  SELECT format('CREATE DATABASE %I', :'development_database')
  WHERE NOT EXISTS (
    SELECT 1 FROM pg_database WHERE datname = :'development_database'
  )\gexec
EOSQL

for migration in /docker-entrypoint-initdb.d/[0-9][0-9][0-9]_*.sql; do
  psql --username "${POSTGRES_USER}" --dbname "${development_database}" --set=ON_ERROR_STOP=1 --file="${migration}"
done
psql --username "${POSTGRES_USER}" --dbname "${development_database}" --set=ON_ERROR_STOP=1 --file=/opt/study_for_job/seeds/development.sql
