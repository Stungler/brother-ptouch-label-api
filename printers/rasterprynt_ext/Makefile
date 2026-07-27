testall: lint test

test:
	python -m unittest discover -s tests -v

lint:
	python -m ruff check rasterprynt tests examples
	python -m ruff format --check rasterprynt tests examples

.PHONY: lint test testall
