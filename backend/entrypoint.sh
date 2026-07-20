#!/bin/sh
set -e

# Strip Windows-style carriage returns if the file was edited on Windows
# (already handled at image build time, but safe to repeat)
sed -i 's/\r$//' "$0" 2>/dev/null || true

echo "Verifying database connection..."
python -c "
import os, sys, time
import psycopg2

host     = os.environ.get('DB_HOST', 'localhost')
port     = os.environ.get('DB_PORT', '5432')
user     = os.environ.get('DB_USER', 'postgres')
password = os.environ.get('DB_PASSWORD', 'postgres')
dbname   = os.environ.get('DB_NAME', 'bdo_leads')

print(f'Connecting to {host}:{port}/{dbname} as {user}...')

for attempt in range(30):
    try:
        conn = psycopg2.connect(
            host=host, port=port, user=user, password=password, dbname=dbname,
            connect_timeout=5,
        )
        conn.close()
        print('Database connection successful.')
        break
    except psycopg2.OperationalError as e:
        print(f'Not ready yet ({attempt + 1}/30): {e}')
        time.sleep(2)
else:
    print('ERROR: Could not connect to the database after 30 attempts.')
    sys.exit(1)
"

echo "Running migrations (safe to run on existing DB only applies missing migrations)..."
python manage.py migrate --noinput

echo "Initializing application..."
python manage.py initialize_app

echo "Starting Django server..."
exec python manage.py runserver 0.0.0.0:8000
