# LaunchPad Conversion Lab

LaunchPad Conversion Lab is a full-stack e-commerce experimentation copilot.
It lets teams create campaign landing-page variants, run KPI simulations, ask Codex for improvements, and compare variant performance.

## Tech Stack

- Frontend: Next.js (App Router, TypeScript, Tailwind)
- Backend: FastAPI (Python), SQLAlchemy, Pydantic
- Database: PostgreSQL (Docker), SQLite (optional local backend-only mode)
- Auth: JWT bearer auth
- AI integration: Codex via CLI (`codex exec`) or API provider mode
- Testing: Pytest, Vitest, Playwright

## Architecture Decisions

- Thin API routes: request parsing/auth only
- Service layer: business workflows (`app/services`)
- Repository layer: DB access (`app/repositories`)
- Strict schemas: all API and Codex payloads validated through Pydantic
- Single Codex boundary: `backend/app/services/codex_service.py`

## Repository Layout

- `backend/app/api`: route handlers
- `backend/app/services`: workflow/business logic
- `backend/app/repositories`: persistence layer
- `backend/app/models`: SQLAlchemy models
- `backend/app/schemas`: Pydantic contracts
- `backend/alembic`: migrations
- `backend/tests`: backend unit/integration tests
- `frontend/app`: pages/routes
- `frontend/components`: UI components
- `frontend/lib`: API client + types
- `frontend/tests`: unit + e2e tests

## Prerequisites

- Docker + Docker Compose (recommended)
- Node.js 20+ (local frontend)
- Python 3.11+ (local backend)
- Codex CLI installed and authenticated for CLI provider mode

Helpful install commands:

macOS (Homebrew):

```bash
brew install --cask docker
brew install node@20 python@3.11 openssl
npm install -g @openai/codex
```

Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin nodejs npm python3.11 python3.11-venv openssl
sudo npm install -g @openai/codex
```

Verify installs:

```bash
docker --version
docker compose version
node --version
python3.11 --version
codex --version
```

## Quick Start (Docker)

1. Copy environment template:

```bash
cp .env.example .env
```

2. Set a non-default JWT secret in `.env` (replace the `SECRET_KEY` value).

If `openssl` is installed:

```bash
openssl rand -hex 32
```

If `openssl` is not installed, you can generate one with Python:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

3. If using Codex CLI mode, authenticate on host:

```bash
codex login
```

4. Start services:

```bash
docker-compose up --build -d
```

5. Open apps:

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Demo Data Behavior (Seamless Defaults)

- On container start, backend runs migrations and seeds baseline demo campaigns automatically.
- Data persists between restarts through the Postgres Docker volume (`pgdata`).

Reset to a clean seeded state (recommended before a live demo):

```bash
docker-compose exec backend sh -lc "DEMO_RESET_ON_START=true python -m app.utils.seed_demo"
```

Hard reset everything (drops Postgres volume, then reseeds on startup):

```bash
docker-compose down -v
docker-compose up --build -d
```

## Local Development (No Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
```

Recommended local backend env adjustments:

- `USE_SQLITE=true`
- `LOCAL_DATABASE_URL=sqlite+pysqlite:///./launchpad.db`
- keep `SECRET_KEY` non-default

Run migrations + API:

```bash
alembic upgrade head
python -m app.utils.seed_demo
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

If you want to run Playwright locally (outside Docker), install browser binaries once:

```bash
npx playwright install --with-deps chromium
```

## Configuration

Primary environment variables (root `.env`):

- `SECRET_KEY`: JWT signing key for app authentication
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT lifetime
- `DATABASE_URL`: Postgres DSN for containerized runtime
- `LOCAL_DATABASE_URL`: SQLite DSN for local backend mode
- `USE_SQLITE`: toggle SQLite backend mode
- `FRONTEND_ORIGIN`: CORS allowlist
- `NEXT_PUBLIC_API_URL`: frontend API base URL
- `CODEX_PROVIDER`: `cli` or `api`
- `CODEX_USE_FALLBACK`: whether deterministic fallback is allowed
- `CODEX_MODEL`: model identifier used in Codex calls

## Codex Integration

Programmatic Codex usage is wired in two main flows:

- Variant generation
  - `POST /campaigns/{campaign_id}/generate-variants`
- Improvement recommendations
  - `POST /campaigns/{campaign_id}/propose-improvements`

All Codex output is schema-validated before persistence.

### CLI Provider Mode (default)

- Backend executes `codex exec` via subprocess.
- Docker mounts host CLI auth (read-only):
  - `${HOME}/.codex/auth.json`
  - `${HOME}/.codex/config.toml`

### API Provider Mode (optional)

Set `CODEX_PROVIDER=api` and configure one of:

- `CODEX_API_KEY`
- `CODEX_API_KEY_FILE`
- `CODEX_API_KEY_ENCRYPTED` + decryption key settings

## Testing

Backend:

```bash
docker-compose exec -T backend pytest -q
```

Frontend unit tests:

```bash
docker-compose exec -T frontend npm run test -- --run
```

Frontend build:

```bash
docker-compose exec -T frontend npm run build
```

Playwright smoke:

```bash
docker-compose exec -T frontend npm run test:e2e
```

## Security Notes

- Do not commit `.env` or `.secrets`.
- Keep Codex auth files private on your host machine.
- Docker auth mounts are read-only.
- JWT currently lives in browser localStorage (MVP tradeoff).
- `docker-compose.yml` credentials/ports are development defaults, not production hardening.

## Troubleshooting

- Codex calls fail in CLI mode:
  - run `codex login` on host
  - confirm backend can see mounted auth files
- 401 errors after login:
  - verify `SECRET_KEY` is set and stable
  - clear browser local storage and sign in again
- CORS issues:
  - ensure `FRONTEND_ORIGIN` includes your frontend URL(s)

## Limitations

- KPI data is simulated.
- Patch format is intentionally constrained.
- No advanced RBAC.
- Not production-hardened by default.
