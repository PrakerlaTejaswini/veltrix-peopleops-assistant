
# Veltrix PeopleOps Assistant

A beginner-friendly HR assistant built with FastAPI, SQLite,
document retrieval, and Google's Gemini API.

## Features

- Answer HR policy questions using supplied documents.
- Read PDF, DOCX, HTML, Markdown, and TXT files.
- Retrieve relevant text chunks using TF-IDF.
- Generate answers using Gemini.
- Validate and record leave requests.
- Store leave requests in SQLite.
- Run locally or with Docker.

## Project Structure

- app/main.py: FastAPI endpoints
- app/config.py: Environment configuration
- app/schemas.py: API request and response models
- app/db.py: SQLite database
- app/ingestion.py: Document reading and chunking
- app/retrieval.py: HR document search
- app/llm.py: Gemini integration
- app/tools.py: Leave validation and database operations
- app/orchestrator.py: Message routing
- tests/: Automated tests
- data/: HR policy documents
- index/: Generated document index and database

## Local Setup

### 1. Create a virtual environment

Windows PowerShell:

    py -m venv .venv
    .\.venv\Scripts\Activate.ps1

### 2. Install dependencies

    python -m pip install -r requirements.txt

### 3. Configure environment

    Copy-Item .env.example .env

Add your Gemini API key to the .env file.

### 4. Add HR documents

Place your HR policy PDF, DOCX, HTML, Markdown, or TXT files
inside the data folder.

### 5. Run the application

    python -m uvicorn app.main:app --reload

### 6. Open API documentation

    http://127.0.0.1:8000/docs

### 7. Build the document index

Call POST /ingest before asking HR policy questions.

## API Endpoints

- GET /health
- POST /chat
- POST /ingest
- POST /leave
- GET /leave/{employee_id}

## Run Tests

    python -m pytest -q

## Run with Docker

    docker compose up --build

Open http://127.0.0.1:8000/docs.

Stop the application:

    docker compose down

## Important Notes

Leave requests are stored as PENDING and are not automatically
approved. This starter project is intended for learning and
demonstration. Add authentication, authorization, audit logging,
and production security controls before handling real employee data.
