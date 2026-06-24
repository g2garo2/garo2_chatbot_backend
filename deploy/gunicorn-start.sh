#!/bin/bash
set -e
source /var/www/garo2/backend/.venv/bin/activate
cd /var/www/garo2/backend
exec gunicorn -k uvicorn.workers.UvicornWorker -w 3 -b 127.0.0.1:8000 app.main:app
