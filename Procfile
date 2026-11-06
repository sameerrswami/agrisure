release: python manage.py migrate --noinput
web: gunicorn agrisure.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --threads 2 --timeout 60
worker: celery -A agrisure worker -l info --concurrency 2
beat: celery -A agrisure beat -l info

