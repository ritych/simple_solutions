.PHONY: test up down logs

test:
	pytest

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api worker
