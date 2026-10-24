# Variables
UV      := uv
MAIN    := pac-man.py
CONFIG  := config.json
MYPY_FLAGS := --warn-return-any --warn-unused-ignores --ignore-missing-imports \
              --disallow-untyped-defs --check-untyped-defs

.PHONY: all install run debug clean lint lint-strict package test

all: run

# Create .venv and install dependencies (uv downloads Python >= 3.10 if needed)
install:
	$(UV) sync

run:
	$(UV) run python $(MAIN) $(CONFIG)

debug:
	$(UV) run python -m pdb $(MAIN) $(CONFIG)

clean:
	find . -path ./.venv -prune -o -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .mypy_cache build dist *.egg-info

# Mandatory lint rule (exact commands from the subject)
lint:
	$(UV) run flake8 .
	$(UV) run mypy . $(MYPY_FLAGS)

lint-strict:
	$(UV) run flake8 .
	$(UV) run mypy . --strict

# Standalone build for itch.io: dist/pac-man/ (folder) and dist/pac-man-linux.zip
package:
	$(UV) run pyinstaller --noconfirm --clean --log-level WARN \
		--distpath dist/bin --workpath build pac-man.spec
	rm -rf dist/pac-man && mkdir -p dist/pac-man/assets
	cp dist/bin/pac-man $(CONFIG) PLAYING.txt .itch.toml dist/pac-man/
	cp assets/spritesheet.png dist/pac-man/assets/
	cd dist && $(UV) run python -m zipfile -c pac-man-linux.zip pac-man
	@echo "Ready: dist/pac-man/ and dist/pac-man-linux.zip"

test:
	$(UV) run --with pytest pytest -q test_pacman.py
