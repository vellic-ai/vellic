.PHONY: up down logs test-webhook

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

test-webhook:
	bash scripts/test-webhook.sh
