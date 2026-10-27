#!/usr/bin/env bash
# One-time database setup for a hosted Postgres (e.g. Neon on Vercel). Run locally with the
# production connection string:  DATABASE_URL='postgres://…' ./setup_db.sh
set -o errexit
: "${DATABASE_URL:?Set DATABASE_URL to the production database first}"
python manage.py migrate --noinput
VERCEL=1 python manage.py createcachetable  # with Vercel settings, so the database cache table is created
python manage.py seed_store
python manage.py seed_help
