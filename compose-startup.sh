#!/usr/bin/env sh

# A simple start up script to get started in docker-compose.
python manage.py migrate && \
    python manage.py createsuperuser

python manage.py runserver 0.0.0.0:8000
