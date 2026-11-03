
import os
from google import genai
from groq import Groq

from app.config import GEMINI_API_KEY, GEMINI_MODEL

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()

NO_ANSWER = (
    "I couldn't find enough information in the provided HR documents "
    "to answer this question."
)


def build_prompt(question: str, context: str) -> str:
    return f"""
You are Veltrix PeopleOps Assistant.

Answer the employee's question using ONLY the HR document context below.

Rules:
1. Do not invent HR policies, dates, balances, or benefits.
2. If the context does not contain enough information, say so.
3. Give clear and concise answers.
4. Respect regional and effective-date information in the context.
5. Mention the relevant source document when possible.

HR DOCUMENT CONTEXT:
{context}

EMPLOYEE QUESTION:
{question}

ANSWER:
"""


def generate_answer(question: str, context: str) -> str:
    if not context or not context.strip():
        return NO_ANSWER

    prompt = build_prompt(question, context)

    # Try Gemini first
    if GEMINI_API_KEY:
        try:
            client = genai.Client(
                api_key=GEMINI_API_KEY,
                http_options={"timeout": 120000}
            )

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )

            answer = getattr(response, "text", None)
            if answer and answer.strip():
                print("LLM provider: Gemini", flush=True)
                return answer.strip()

        except Exception as error:
            print(
                f"Gemini failed: {type(error).__name__}: {error}",
                flush=True
            )

    # Use Groq if Gemini fails
    if GROQ_API_KEY:
        try:
            client = Groq(api_key=GROQ_API_KEY)

            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=1000,
                reasoning_effort="low"
            )

            answer = response.choices[0].message.content

            if answer and answer.strip():
                print("LLM provider: Groq", flush=True)
                return answer.strip()

        except Exception as error:
            print(
                f"Groq failed: {type(error).__name__}: {error}",
                flush=True
            )

    return "Both AI providers are currently unavailable. Please try again later."
