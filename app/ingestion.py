
import re
from pathlib import Path
from datetime import datetime

from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document

from app.config import DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP


SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".txt", ".md", ".html", ".htm"
}


def read_document(file_path):
    file_path = Path(file_path)
    extension = file_path.suffix.lower()

    if extension == ".pdf":
        reader = PdfReader(str(file_path))
        pages = []

        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(f"\n[Page {page_number}]\n{page_text}")

        return "\n".join(pages)

    if extension == ".docx":
        document = Document(str(file_path))
        paragraphs = [
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        for table in document.tables:
            for row in table.rows:
                row_text = " | ".join(
                    cell.text.strip() for cell in row.cells
                )
                if row_text.strip():
                    paragraphs.append(row_text)

        return "\n".join(paragraphs)

    if extension in [".txt", ".md"]:
        return file_path.read_text(
            encoding="utf-8", errors="ignore"
        )

    if extension in [".html", ".htm"]:
        html = file_path.read_text(
            encoding="utf-8", errors="ignore"
        )
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator="\n", strip=True)

    return ""


def extract_metadata(text, filename):
    """Extract document metadata from the full document text."""

    metadata = {
        "filename": filename,
        "document_id": None,
        "version": None,
        "effective_date": None,
        "region": "GLOBAL",
    }

    patterns = {
        "document_id": r"Document ID\s*[\n:|]+\s*([A-Z0-9_-]+)",
        "version": r"Version\s*[\n:|]+\s*([0-9]+(?:\.[0-9]+)*)",
        "effective_date": (
            r"Effective date\s*[\n:|]+\s*"
            r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})"
        ),
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()

            if field == "effective_date":
                try:
                    metadata[field] = datetime.strptime(
                        value, "%d %B %Y"
                    ).date().isoformat()
                except ValueError:
                    metadata[field] = None
            else:
                metadata[field] = value

    lower_name = filename.lower()

    if "india" in lower_name:
        metadata["region"] = "INDIA"
    elif "germany" in lower_name:
        metadata["region"] = "GERMANY"
    elif "_us_" in lower_name or lower_name.startswith("us_"):
        metadata["region"] = "US"

    return metadata


def split_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    text = " ".join(text.split())

    if not text.strip():
        return []

    if overlap >= chunk_size:
        raise ValueError(
            "Chunk overlap must be smaller than chunk size."
        )

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


def load_documents(data_folder=None):
    folder = Path(data_folder) if data_folder else Path(DATA_DIR)

    if not folder.exists():
        raise FileNotFoundError(f"Data folder not found: {folder}")

    documents = []

    files = sorted(
        path for path in folder.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
        and path.name.lower() != "manifest.json"
    )

    print(f"Found {len(files)} supported documents.")

    for file_path in files:
        try:
            print(f"Reading: {file_path.name}")

            text = read_document(file_path)

            if not text.strip():
                print(f"WARNING: No text extracted from {file_path.name}")
                continue

            metadata = extract_metadata(text, file_path.name)
            chunks = split_text(text)

            for chunk_number, chunk in enumerate(chunks):
                documents.append({
                    "text": chunk,
                    "source": str(file_path.relative_to(folder)),
                    "filename": file_path.name,
                    "chunk": chunk_number,
                    **metadata,
                })

            print(f"  Extracted {len(chunks)} chunks")

        except Exception as error:
            print(f"ERROR reading {file_path.name}: {error}")

    print(f"\nTotal chunks created: {len(documents)}")
    return documents


if __name__ == "__main__":
    documents = load_documents()
    print(f"Ingestion completed: {len(documents)} chunks")
