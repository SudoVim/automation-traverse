.PHONY: check
check: mypy format-check

.PHONY: mypy
mypy:
	@mypy automation_traverse

.PHONY: format
format:
	@git ls-files | grep "\.py$ " | xargs black

.PHONY: format-check
format-check:
	@git ls-files | grep "\.py$ " | xargs black --check

.PHONY: test
test:
	@py.test --cov=automation_traverse --cov-report=term-missing .
