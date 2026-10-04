.PHONY: format lint typecheck test coverage build publication-candidate docs clean release
format:
	python -m ruff format src tests
lint:
	python -m ruff check .
typecheck:
	python -m mypy src
test:
	python -m pytest
coverage:
	python -m pytest --cov=manga_director --cov-report=term-missing
build:
	python scripts/build_publication_candidate.py
publication-candidate: build
docs:
	@echo "Documentation is Markdown under docs/."
clean:
	@echo "Remove ignored build artefacts manually or use scripts/reset."
release: lint typecheck test build
