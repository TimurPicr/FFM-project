from typing import Dict
import json
import re

from src.synopsis_gen.llm.yandex_client import LLMClient

def try_parse_json(txt: str) -> Dict:
    t = (txt or "").strip()
    if not t.startswith("{"):
        m = re.search(r"\{.*\}", t, flags=re.S)
        if m:
            t = m.group(0)
    return json.loads(t)

def llm_json(llm: LLMClient, system: str, user: str, retries: int = 2) -> Dict:
    last = None
    for _ in range(retries + 1):
        out = llm.chat(system, user)
        try:
            return try_parse_json(out)
        except Exception as e:
            last = e
            user = user + "\n\nВНИМАНИЕ: верни ТОЛЬКО валидный JSON, без markdown и без комментариев."
    raise RuntimeError(f"LLM did not return valid JSON: {last}")
