VENV	= .venv
MAIN	= fly-in.py
ARGS	= config.txt


.PHONY: all install run debug lint lint-strict  clean fclean re

all: run

$(VENV): pyproject.toml
	uv sync

install: $(VENV)

run: $(VENV)
	uv run $(MAIN) $(ARGS)

debug: $(VENV)
	uv run python -m pdb $(MAIN) $(ARGS)

lint: $(VENV)
	uv run flake8 .
	uv run mypy . \
		--warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict: $(VENV)
	uv run flake8 . --exclude=.venv,build,dist,maps
	uv run mypy . --strict


clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

fclean: clean
	rm -rf $(VENV)
	rm -f uv.lock

re: fclean all
