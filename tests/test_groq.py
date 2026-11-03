
import pytest
from groq import Groq
from app.config import GROQ_API_KEY, GROQ_MODEL

@pytest.mark.integration
def test_groq_connection():
    if not GROQ_API_KEY:
        pytest.skip("GROQ_API_KEY is not configured")

    client = Groq(api_key=GROQ_API_KEY, timeout=15)

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "user", "content": "Say hello in one short sentence."}
        ],
        max_tokens=50,
        temperature=0,
        reasoning_effort="low"
    )

    answer = response.choices[0].message.content
    assert answer is not None
    assert len(answer.strip()) > 0
