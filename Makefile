.PHONY: backend-test backend-run backend-seed frontend-dev

backend-test:
	cd backend && ../.venv/bin/pytest

backend-run:
	cd backend && ../.venv/bin/uvicorn app.main:app --reload

backend-seed:
	cd backend && ../.venv/bin/python -m app.utils.seed_demo

frontend-dev:
	cd frontend && npm run dev
