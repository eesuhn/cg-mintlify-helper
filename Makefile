VENV = .venv
CONFIG = .config
OS := $(shell uname -s)

all: venv

venv: $(VENV)/bin/activate

$(VENV)/bin/activate: pyproject.toml
	@uv sync
	@uv run pre-commit install --config=$(CONFIG)/pre-commit.yaml

%:
	@:

upgrade:
	@uv sync --upgrade
	@git add uv.lock

format:
	@uv run ruff format

check:
	@uv run ruff check

check-fix:
	@uv run ruff check --fix

clean:
	rm -rf .pytest_cache/ .ruff_cache/
	@uvx pyclean .

test:
	@uv run pytest $(filter-out $@,$(MAKECMDGOALS))

run:
	@uv run -m main $(filter-out $@,$(MAKECMDGOALS))

add-mint:
	@uv run -m main add-mint

mdx-demo:
	@uv run -m main convert-mdx --api-mode demo

mdx-pro:
	@uv run -m main convert-mdx --api-mode pro

.PHONY: all venv upgrade format check check-fix clean test \
		run add-mint mdx-demo mdx-pro
