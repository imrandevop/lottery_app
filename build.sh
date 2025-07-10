#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Create cache table (ignore if already exists)
python manage.py createcachetable lottery_cache_table || echo "Cache table already exists or using memory cache"