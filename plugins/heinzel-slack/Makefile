.DEFAULT_GOAL := help
TOOLING ?= heinzel-plugin-tools @ https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/releases/download/tools-v0.3.7/heinzel_plugin_tools-0.3.7-py3-none-any.whl\#sha256=ac959c164e3726f86311c86fa9d3b4a3cbc82a6b4f81fae8bf462ee8103bd359
unexport TOOLING CORE TAG REGISTRY
export HZ_PLUGIN_TOOLING := $(value TOOLING)
export PLUGIN_CORE := $(value CORE)
export PLUGIN_TAG := $(value TAG)
export PLUGIN_REGISTRY := $(value REGISTRY)
MAKEOVERRIDES =
PLUGIN := uv run --quiet --no-project --with "$$HZ_PLUGIN_TOOLING" hz-plugin

.PHONY: help setup fix check-fast check test lock preview build acceptance audit release preflight publish
help:
	@echo 'make setup; make check-fast; make check; make preview; make build; make acceptance'
	@echo 'make lock refreshes this plugin dependency lock; CORE=<wheel> selects a candidate SDK.'
	@echo 'make release previews; make publish dispatches the protected release workflow.'
setup fix check-fast check test lock preview build acceptance audit release preflight:
	@$(PLUGIN) $@
publish:
	@$(PLUGIN) publish
