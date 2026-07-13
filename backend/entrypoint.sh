#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
python -c "
import os, sys, time
import psycopg2

host = os.environ.get('DB_HOST', 'postgres')
port = os.environ.get('DB_PORT', '5432')
user = os.environ.get('DB_USER', 'postgres')
password = os.environ.get('DB_PASSWORD', 'postgres')
dbname = os.environ.get('DB_NAME', 'bdo_leads')

for attempt in range(30):
    try:
        conn = psycopg2.connect(
            host=host, port=port, user=user, password=password, dbname=dbname
        )
        conn.close()
        print('PostgreSQL is ready.')
        break
    except psycopg2.OperationalError:
        print(f'Waiting for PostgreSQL... ({attempt + 1}/30)')
        time.sleep(2)
else:
    print('Could not connect to PostgreSQL.')
    sys.exit(1)
"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Initializing application..."
python manage.py initialize_app

echo "Starting Django server..."
exec python manage.py runserver 0.0.0.0:8000
