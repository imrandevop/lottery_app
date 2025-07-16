#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Only do static files during build (no DB operations)
python manage.py collectstatic --no-input

# Skip migrations and cache table creation during build
echo "Build completed - migrations will run at startup"