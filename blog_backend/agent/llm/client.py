from openai import OpenAI

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
    model=OPENAI_MODEL,
)
