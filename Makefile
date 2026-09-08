SHELL := /bin/bash

.PHONY: setup check test scan
setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
check:
	python3 -m json.tool opencode.jsonc >/dev/null
	@echo "opencode.jsonc: valid JSON"
test:
	.venv/bin/pytest -q
scan:
	./scripts/scan-projects
