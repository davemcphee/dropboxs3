.PHONY: help

help: ## This help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

test: ## Run python tests
	@pytest

dc-bul: ## docker compose build, up, logs -f
	@docker compose build && docker compose up -d && docker compose logs -f
