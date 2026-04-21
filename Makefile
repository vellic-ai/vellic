.PHONY: hooks up down logs test-webhook release

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

release:
	@if [ -z "$(VERSION)" ]; then echo "Usage: make release VERSION=x.y.z"; exit 1; fi
	@echo "Tagging v$(VERSION)..."
	git tag -a "v$(VERSION)" -m "Release v$(VERSION)"
	git push origin "v$(VERSION)"
	@echo "Tag v$(VERSION) pushed — CI will build images and create a draft release."
