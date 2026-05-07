# Cube Rail Game Platform

This is a comprehensive, scalable web-based platform hosting asynchronous multiplayer "cube rail" board games.

## Monorepo Structure

- `/backend`: FastAPI Python server acting as an API gateway, WebSocket manager, and Game Engine host.
- `/frontend`: Vite + React SPA handling user interaction, rendering the SVG game board, and subscribing to live events.
- `/shared`: Common TypeScript types for frontend parsing of game state objects.

## Local Development

### 1. Database (Docker Compose)
A PostgreSQL database and Redis instance are provided via `docker-compose`.
```bash
docker-compose up -d
```

### 2. Backend (FastAPI)
Navigate to the `/backend` directory.

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations to initialize schema
alembic upgrade head

# Start API dev server
uvicorn app.main:app --reload
```

### 3. Frontend (React / Vite)
Navigate to the `/frontend` directory.

```bash
cd frontend
npm install
npm run dev
```

## Testing

**Backend (Pytest):**
```bash
cd backend
pytest
```

**Frontend (Vitest):**
```bash
cd frontend
npx vitest run
```

## Architecture Notes

For full architectural decision records, component trees, and data flow diagrams, refer to `ARCHITECTURE.md`.
