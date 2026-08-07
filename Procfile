release: python manage.py migrate
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --log-level debug --capture-output --access-logfile - --error-logfile -
