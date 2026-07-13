# BDO Lead Management

A full-stack web application for Business Development Officers (BDOs) to manage leads, track activities, and integrate external services.

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Backend  | Django, Django REST Framework       |
| Database | PostgreSQL                          |
| Frontend | React, React Router, Axios, Vite    |
| Auth     | Django session authentication       |
| DevOps   | Docker Compose                      |

## Quick Start (Docker)

**Prerequisites:** Docker and Docker Compose

```bash
git clone <repository-url>
cd BDO-Project
cp .env.example .env
docker compose up --build
```

Open **http://localhost:5173** and sign in:

| Username | Password |
|----------|----------|
| `admin`  | `admin`  |

Docker automatically:

- Starts `postgres`, `backend`, and `frontend` containers
- Waits for PostgreSQL to be healthy before starting the backend
- Runs Django migrations on startup
- Creates the default admin user if it doesn't exist
- Seeds sample leads, activities, and integrations

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv ../venv
..\venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
cp .env.example .env           # Set USE_SQLITE=True if no PostgreSQL
python manage.py migrate
python manage.py initialize_app
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
BDO-Project/
├── .env                    # Docker & app configuration
├── docker-compose.yml      # postgres + backend + frontend
├── backend/
│   ├── accounts/           # Authentication
│   ├── dashboard/          # Dashboard stats API
│   ├── leads/              # Lead CRUD API
│   ├── activity/           # Activity timeline
│   ├── integrations/       # Integration placeholders
│   ├── Dockerfile
│   └── entrypoint.sh       # Wait for DB, migrate, init, run
└── frontend/
    ├── src/
    │   ├── components/     # SkillChips, StatusBadge, layout
    │   ├── pages/          # Login, Dashboard, Leads, Activity, Integrations
    │   ├── services/       # Axios API client
    │   └── context/        # Auth context
    └── Dockerfile
```

## Lead Model

| Field            | Type       | Description                    |
|------------------|------------|--------------------------------|
| `title`          | string     | Required job/lead title        |
| `url`            | string     | Source URL                     |
| `budget`         | string     | Display budget text            |
| `budget_min`     | float      | Minimum budget                 |
| `budget_max`     | float      | Maximum budget                 |
| `skills`         | JSON array | Skill tags                     |
| `job_type`       | string     | e.g. Fixed Price, Hourly       |
| `posted_at`      | datetime   | When the job was posted        |
| `fetched_at`     | datetime   | Required — when lead was fetched |
| `status`         | string     | Default: `pending`             |
| `skip_reason`    | string     | Reason if skipped              |
| `total_proposals`| int        | Number of proposals            |

## API Endpoints

| Method | Endpoint              | Description                |
|--------|-----------------------|----------------------------|
| POST   | `/api/login/`         | Authenticate user          |
| POST   | `/api/logout/`        | End session                |
| GET    | `/api/dashboard/`     | Dashboard statistics       |
| GET    | `/api/leads/`         | List leads (search/filter) |
| POST   | `/api/leads/`         | Create lead                |
| GET    | `/api/leads/:id/`     | Get lead detail            |
| PATCH  | `/api/leads/:id/`     | Update lead                |
| DELETE | `/api/leads/:id/`     | Delete lead                |
| GET    | `/api/activity/`      | Activity timeline          |
| GET    | `/api/integrations/`  | Integration list           |

## Configuration

All configuration is stored in the root `.env` file. Copy `.env.example` to `.env` before starting.

Key variables:

| Variable       | Default              | Description              |
|----------------|----------------------|--------------------------|
| `DB_NAME`      | `bdo_leads`          | PostgreSQL database name |
| `DB_USER`      | `postgres`           | PostgreSQL user          |
| `DB_PASSWORD`  | `postgres`           | PostgreSQL password      |
| `BACKEND_PORT` | `8000`               | Backend host port        |
| `FRONTEND_PORT`| `5173`               | Frontend host port       |

## Future Enhancements

The architecture supports adding:

- Multiple user roles and lead assignment
- Lead comments and resume uploads
- Job scraping and AI recommendations
- Email integration (Gmail/Outlook OAuth)
- Activity analytics and notifications
