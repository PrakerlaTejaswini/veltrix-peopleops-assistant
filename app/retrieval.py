
import json
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import DATA_DIR, INDEX_DIR, TOP_K, APP_TODAY
from app.ingestion import load_documents


INDEX_DIR = Path(INDEX_DIR)
DOCUMENTS_FILE = INDEX_DIR / "documents.json"
VECTORIZER_FILE = INDEX_DIR / "tfidf_vectorizer.joblib"
MATRIX_FILE = INDEX_DIR / "tfidf_matrix.joblib"


def is_effective(document):
    effective_date = document.get("effective_date")

    if not effective_date:
        return True

    try:
        from datetime import date
        return date.fromisoformat(effective_date) <= APP_TODAY
    except (ValueError, TypeError):
        return False


def build_index():
    print("Loading HR documents...")
    documents = load_documents(DATA_DIR)

    documents = [
        document for document in documents
        if document.get("text", "").strip()
    ]

    if not documents:
        print("No usable documents found.")
        return 0

    texts = [document["text"] for document in documents]

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=50000
    )

    matrix = vectorizer.fit_transform(texts)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    with open(DOCUMENTS_FILE, "w", encoding="utf-8") as file:
        json.dump(documents, file, indent=2, ensure_ascii=False)

    joblib.dump(vectorizer, VECTORIZER_FILE)
    joblib.dump(matrix, MATRIX_FILE)

    print(f"Index built successfully. Total chunks: {len(texts)}")
    return len(texts)


def load_index():
    required_files = [
        DOCUMENTS_FILE,
        VECTORIZER_FILE,
        MATRIX_FILE
    ]

    if not all(path.exists() for path in required_files):
        print("Index files missing. Building index...")
        build_index()

    if not all(path.exists() for path in required_files):
        return None, None, None

    with open(DOCUMENTS_FILE, "r", encoding="utf-8") as file:
        documents = json.load(file)

    vectorizer = joblib.load(VECTORIZER_FILE)
    matrix = joblib.load(MATRIX_FILE)

    return documents, vectorizer, matrix


def search_documents(question, top_k=None):
    if not question or not question.strip():
        return []

    documents, vectorizer, matrix = load_index()

    if documents is None:
        return []

    if top_k is None:
        top_k = TOP_K

    question_vector = vectorizer.transform([question])
    scores = cosine_similarity(question_vector, matrix).flatten()

    # Remove future-effective documents before ranking.
    eligible = [
        index for index, document in enumerate(documents)
        if is_effective(document)
    ]

    ranked_indices = sorted(
        eligible,
        key=lambda index: scores[index],
        reverse=True
    )

    results = []

    for index in ranked_indices:
        if scores[index] <= 0:
            continue

        result = documents[index].copy()
        result["score"] = float(scores[index])
        results.append(result)

        if len(results) >= top_k:
            break

    return results


if __name__ == "__main__":
    total = build_index()
    print(f"Index built successfully. Total chunks: {total}")
