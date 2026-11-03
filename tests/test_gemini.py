
import pytest
from google import genai
from app.config import GEMINI_API_KEY, GEMINI_MODEL

@pytest.mark.integration
def test_gemini_connection():
    if not GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY is not configured")

    client = genai.Client(
        api_key=GEMINI_API_KEY,
        http_options={"timeout": 30000}
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents="Reply with exactly: OK"
    )

    assert response.text
