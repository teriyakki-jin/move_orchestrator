import json
import time
import re
from openai import OpenAI
from pydantic import BaseModel
from .config import get_settings

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def generate_structured(
    system_prompt: str,
    user_content: str,
    response_schema: type,
    temperature: float = 0.2,
) -> dict:
    """OpenAI SDK로 structured output 호출 (Rate Limit 재시도 포함)"""
    settings = get_settings()
    client = get_client()

    for attempt in range(3):
        try:
            completion = client.beta.chat.completions.parse(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                response_format=response_schema,
                temperature=temperature,
                max_tokens=4096,
            )
            parsed = completion.choices[0].message.parsed
            return parsed.model_dump() if parsed else {}
        except Exception as e:
            err = str(e)
            if "429" in err or "rate_limit" in err.lower():
                m = re.search(r"(\d+)s", err)
                wait = int(m.group(1)) + 2 if m else (15 * (attempt + 1))
                print(f"[Rate Limit] {wait}초 대기 후 재시도 ({attempt+1}/3)...")
                time.sleep(wait)
            else:
                print(f"[OpenAI Error] {err}")
                break
    return {}
