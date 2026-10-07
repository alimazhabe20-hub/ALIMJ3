.PHONY: install run test quality docker-up docker-down clean

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt

run:
	python -m bot.main

test:
	python -m unittest discover -s tests -v

quality:
	python scripts/run_quality.py

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache
