.DEFAULT_GOAL := help
PLUGIN := uv run --no-project --script scripts/plugins.py
unexport NAME CORE BASE CONTRACT
MAKEOVERRIDES =
export PLUGIN_NAME := $(value NAME)
export PLUGIN_CORE := $(value CORE)
export PLUGIN_BASE := $(value BASE)
export PLUGIN_CONTRACT := $(value CONTRACT)

.PHONY: setup install check-fast preflight policies secrets pr help list plan lock test check build profile release preview acceptance audit tooling-check
help:
	@echo 'make check NAME=resource [CORE=/path/to/core.whl]'
	@echo 'make lock NAME=<plugin> CORE=<compatible-core.whl>'
	@echo 'make preview|test|build|acceptance|release NAME=<plugin> [CORE=<wheel>]'
	@echo 'make profile CORE=<wheel>; make tooling-check'
list:
	@$(PLUGIN) list
plan:
	@$(PLUGIN) plan
lock:
	@$(PLUGIN) lock
test:
	@$(PLUGIN) test
check:
	@$(PLUGIN) check
build:
	@$(PLUGIN) build
preview:
	@$(PLUGIN) preview
acceptance:
	@$(PLUGIN) acceptance
profile:
	@$(PLUGIN) profile
release:
	@$(PLUGIN) release
audit:
	@$(PLUGIN) audit
tooling-check:
	@uv run --group tooling ruff check scripts tests
	@uv run --group tooling ruff format --check scripts tests
	@uv run --group tooling pytest tests -q
	@uv run --group tooling actionlint
	@uv run --group tooling zizmor --offline --quiet .github

install:
	@uv sync --all-groups --quiet
	@uv run --no-project --script scripts/tools.py install
setup: install
	@uv run --group tooling prek install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
check-fast: tooling-check
policies:
	@uv run --group tooling python scripts/check_policy.py
secrets:
	@uv run --no-project --script scripts/tools.py run gitleaks git --redact --no-banner
preflight: tooling-check policies secrets
pr:
	@bash scripts/pr.sh "$(TITLE)"
