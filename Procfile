release: python manage.py collectstatic --noinput && python manage.py migrate
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 120
