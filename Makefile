.PHONY: check
check: mypy format-check

.PHONY: mypy
mypy:
	@pipenv run mypy .

.PHONY: pyright
pyright:
	@pipenv run basedpyright --warnings

.PHONY: format
format:
	@pipenv run isort --profile black .
	@pipenv run black .

.PHONY: format-check
format-check:
	@pipenv run isort --profile black --check-only .
	@pipenv run black --check .

.PHONY: test
test:
	@pipenv run py.test --cov=automation_traverse --cov-report=term-missing .

.PHONY: update-dependencies
update-dependencies:
	pip3 uninstall automation-entities
	pip3 install git+https://github.com/SudoVim/automation-entities
