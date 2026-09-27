release: cd backend && python manage.py migrate --noinput
web: gunicorn --chdir backend backend.wsgi --log-file -
