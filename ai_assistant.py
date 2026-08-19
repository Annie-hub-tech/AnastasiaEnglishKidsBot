import os
from pathlib import Path
from openai import AsyncOpenAI

SYSTEM_PROMPT_FILE = Path(__file__).parent / "AI_SYSTEM_PROMPT.md"
KNOWLEDGE_BASE_FILE = Path(__file__).parent / "knowledge_base.md"

KIE_API_KEY = os.getenv("KIE_AI_ASSISTANT_KEY")

client = None

if KIE_API_KEY:
    client = AsyncOpenAI(
    api_key=KIE_API_KEY,
    base_url="https://api.kie.ai/gemini-2.5-flash/v1"
)

def load_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


SYSTEM_PROMPT = load_file(SYSTEM_PROMPT_FILE)
KNOWLEDGE_BASE = load_file(KNOWLEDGE_BASE_FILE)


async def ask_ai(question: str) -> str:
    """
    Отправляет вопрос родителя в Kie.ai с системным промптом
    и базой знаний Анастасии Александровны.
    """

    if not client:
        raise RuntimeError("KIE_AI_ASSISTANT_KEY is not set")

    try:
        print("Calling Kie.ai")

        response = await client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "system",
                    "content": KNOWLEDGE_BASE
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
        )

        answer = response.choices[0].message.content

        print("Kie.ai response generated")

        return answer

    except Exception as error:
        print(
            "Kie.ai error:",
            type(error).__name__,
            str(error)
        )
        raise