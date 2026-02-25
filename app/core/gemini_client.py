import json
from google import genai
from google.genai import types
from pydantic import BaseModel
from .config import get_settings

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        settings = get_settings()
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def generate_structured(
    system_prompt: str,
    user_content: str,
    response_schema: type,
    temperature: float = 0.2,
) -> dict:
    """google-genai SDK로 structured output 호출 (Rate Limit 재시도 포함)"""
    import time
    settings = get_settings()
    client = get_client()

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=temperature,
        response_mime_type="application/json",
        response_schema=response_schema,
        max_output_tokens=4096,
    )

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=user_content,
                config=config,
            )
            return json.loads(response.text)
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                # Rate Limit: 재시도 대기 시간 추출 후 대기
                import re
                m = re.search(r"retryDelay.*?(\d+)s", err)
                wait = int(m.group(1)) + 2 if m else (15 * (attempt + 1))
                print(f"[Rate Limit] {wait}초 대기 후 재시도 ({attempt+1}/3)...")
                time.sleep(wait)
            else:
                break  # 다른 에러면 재시도 불필요
    return {}


def generate_text(
    system_prompt: str,
    user_content: str,
    temperature: float = 0.3,
) -> str:
    """일반 텍스트 생성"""
    settings = get_settings()
    client = get_client()

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=temperature,
        max_output_tokens=4096,
    )
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=user_content,
        config=config,
    )
    return response.text
