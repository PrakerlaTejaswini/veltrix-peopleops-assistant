
install:
	python -m pip install -r requirements.txt

run:
	python -m uvicorn app.main:app --reload

test:
	python -m pytest -q

ingest:
	curl -X POST http://127.0.0.1:8000/ingest

docker-build:
	docker compose build

docker-run:
	docker compose up --build

docker-stop:
	docker compose down
