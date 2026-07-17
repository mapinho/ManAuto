.PHONY: dev test lint format seed-demo seed-petribu plano migrate makemigrations shell down build

dev:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

test:
	docker compose run --rm web pytest --cov --cov-report=term-missing

lint:
	docker compose run --rm web ruff check .
	docker compose run --rm web ruff format --check .

format:
	docker compose run --rm web ruff check --fix .
	docker compose run --rm web ruff format .

migrate:
	docker compose run --rm web python manage.py migrate

makemigrations:
	docker compose run --rm web python manage.py makemigrations

seed-demo:
	docker compose run --rm web python manage.py seed_demo

seed-petribu:
	docker compose run --rm web python manage.py seed_petribu

plano:
	docker compose run --rm web python manage.py recalcula_plano

shell:
	docker compose run --rm web python manage.py shell
