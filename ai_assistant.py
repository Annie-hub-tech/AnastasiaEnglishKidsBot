import os
from pathlib import Path

from openai import AsyncOpenAI


PROJECT_DIR = Path(__file__).resolve().parent
SYSTEM_PROMPT_PATH = PROJECT_DIR / "AI_SYSTEM_PROMPT.md"
KNOWLEDGE_BASE_PATH = PROJECT_DIR / "knowledge_base.md"

KIE_AI_ASSISTANT_KEY = os.getenv("KIE_AI_ASSISTANT_KEY", "").strip()
client = (
    AsyncOpenAI(
        api_key=KIE_AI_ASSISTANT_KEY,
        base_url="https://api.kie.ai/gemini-2.5-flash/v1",
    )
    if KIE_AI_ASSISTANT_KEY
    else None
)


def load_text_file(file_path: Path):
    try:
        return file_path.read_text(encoding="utf-8")
    except OSError as error:
        print("Kie.ai error: unable to load", file_path.name, str(error))
        raise


async def ask_ai(question: str):
    """Send a parent question to Kie.ai and return only the answer text."""
    if client is None:
        error = "KIE_AI_ASSISTANT_KEY is not set"
        print("Kie.ai error:", error)
        raise RuntimeError(error)

    system_prompt = load_text_file(SYSTEM_PROMPT_PATH)
    knowledge_base = load_text_file(KNOWLEDGE_BASE_PATH)

    try:
        response = await client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "system",
                    "content": knowledge_base,
                },
                {
                    "role": "user",
                    "content": question,
                },
            ],
            temperature=0.3,
        )
    except Exception as error:
        print("Kie.ai error:", type(error).__name__, str(error))
        raise

    print("Kie.ai response generated")
    return response.choices[0].message.content
