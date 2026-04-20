.PHONY: hooks up down logs test-webhook

hooks:
	git config core.hooksPath .githooks
	@echo "git hooks configured (.githooks)"

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

test-webhook:
	bash scripts/test-webhook.sh
