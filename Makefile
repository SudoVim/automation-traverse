.PHONY: all
all: check

.PHONY: check
check: pyright format-check test

.PHONY: pyright
pyright:
	@uv run basedpyright --warnings

.PHONY: format
format:
	@uv run isort --profile black .
	@uv run black .

.PHONY: ci
ci: format pyright

.PHONY: format-check
format-check:
	@$(MAKE) format-check-isort
	@$(MAKE) format-check-black

.PHONY: format-check-isort
format-check-isort:
	@uv run isort --profile black --check-only .

.PHONY: format-check-black
format-check-black:
	@uv run black --check .

.PHONY: test
test:
	@uv run py.test --cov=automation_traverse --cov-report=term-missing .
