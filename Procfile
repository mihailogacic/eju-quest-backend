release: python core/manage.py makemigrations && python core/manage.py migrate
web: gunicorn core.wsgi --chdir core --log-file -
worker: celery -A core.celery worker --loglevel=info
