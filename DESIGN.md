
# Veltrix PeopleOps Assistant - Design

## 1. Overview

The application answers employee HR questions using document
retrieval and Gemini. It also provides basic leave request
validation and storage.

## 2. Architecture

    Employee
       |
       v
    FastAPI (main.py)
       |
       v
    Orchestrator (orchestrator.py)
       |
       +---------------------+
       |                     |
       v                     v
    Retrieval              Leave Tools
    retrieval.py           tools.py
       |                     |
       v                     v
    HR Documents           SQLite Database
       |
       v
    Gemini (llm.py)
       |
       v
    HR Answer

## 3. Document Ingestion

1. HR documents are placed in the data folder.
2. ingestion.py extracts their text.
3. Long text is divided into overlapping chunks.
4. retrieval.py saves chunks in a local JSON index.

## 4. Retrieval-Augmented Generation

1. The employee submits an HR question.
2. TF-IDF converts the document chunks and question into vectors.
3. Cosine similarity ranks the chunks.
4. The most relevant chunks are passed to Gemini.
5. Gemini generates an answer based on the supplied context.

If relevant information is missing, the assistant should say
that it could not find enough information.

## 5. Leave Management

1. The employee provides leave dates and a reason.
2. The application validates the dates.
3. A valid request is stored in SQLite with PENDING status.
4. The employee can view recorded requests.

Submitting a request does not mean the leave has been approved.

## 6. Database

The leave_requests table contains:

- id
- employee_id
- start_date
- end_date
- reason
- status

SQLite is used because it is simple to configure for a local demo.

## 7. Configuration

Secrets and environment-specific settings are loaded from .env.
The actual .env file must not be committed to source control.

## 8. Limitations and Improvements

- Add authentication and employee-level authorization.
- Implement server-side confirmation for leave submissions.
- Add audit logs and request ownership checks.
- Use a persistent embedding-based vector store for larger datasets.
- Add OCR for scanned PDFs and images.
- Add robust tests, monitoring, and error handling.
- Review employee data privacy and retention requirements.
