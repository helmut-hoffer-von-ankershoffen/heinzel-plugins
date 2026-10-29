.DEFAULT_GOAL := help
PLUGIN := uv run --frozen --group tooling hz-plugin
ifneq ($(origin TOOLING),undefined)
export HZ_PLUGIN_TOOLING := $(value TOOLING)
PLUGIN := uv run --quiet --no-project --with "$$HZ_PLUGIN_TOOLING" hz-plugin
endif
unexport NAME CORE BASE CONTRACT TAG TEMPLATE REF REGISTRY PRESET
MAKEOVERRIDES =
export PLUGIN_NAME := $(value NAME)
export PLUGIN_CORE := $(value CORE)
export PLUGIN_BASE := $(value BASE)
export PLUGIN_CONTRACT := $(value CONTRACT)
export PLUGIN_TAG := $(value TAG)
export PLUGIN_TEMPLATE := $(value TEMPLATE)
export PLUGIN_TEMPLATE_REF := $(value REF)
export PLUGIN_REGISTRY := $(value REGISTRY)
export PLUGIN_PRESET := $(value PRESET)

.PHONY: setup install check-fast preflight policies secrets pr help new list plan lock test check build profile release publish preview acceptance audit tooling-check
help:
	@echo 'make check NAME=resource [CORE=/path/to/core.whl]'
	@echo 'make lock NAME=<plugin> CORE=<compatible-core.whl>'
	@echo 'make preview|test|build|acceptance|release NAME=<plugin> [CORE=<wheel>]'
	@echo 'make profile CORE=<wheel>; make tooling-check'
list:
	@$(PLUGIN) list
new:
	@$(PLUGIN) new
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
publish:
	@$(PLUGIN) publish
audit:
	@$(PLUGIN) audit
tooling-check:
	@uv run --group tooling ruff check scripts tests src/heinzel_plugin_tools
	@uv run --group tooling ruff format --check scripts tests src/heinzel_plugin_tools
	@uv run --group tooling pytest tests -q
	@uv run --group tooling actionlint
	@uv run --group tooling zizmor --offline --quiet .github

install:
	@uv sync --all-groups --quiet
	@uv run --no-project --script scripts/tools.py install
setup: install
	@uv run --group tooling prek install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
check-fast:
	@if [ -n "$$PLUGIN_NAME" ]; then $(PLUGIN) check-fast; else make --no-print-directory tooling-check; fi
policies:
	@uv run --group tooling python scripts/check_policy.py
secrets:
	@uv run --no-project --script scripts/tools.py run gitleaks git --redact --no-banner
preflight: tooling-check policies secrets
	@if [ -n "$$PLUGIN_NAME" ]; then $(PLUGIN) preflight; fi
fix:
	@$(PLUGIN) fix
pr:
	@bash scripts/pr.sh "$(TITLE)"
