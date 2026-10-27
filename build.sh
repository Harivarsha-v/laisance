#!/usr/bin/env bash
# Render build step: install, collect static files, migrate and load the collection + help content.
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py seed_store
python manage.py seed_help
