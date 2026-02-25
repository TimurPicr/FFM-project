from src.synopsis_gen.config import YANDEX_MODEL_URI_TEMPLATE, YANDEX_CLOUD_API_KEY, YANDEX_FOLDER_ID, LLM_TEMPERATURE, LLM_MAX_TOKENS, DEBUG
from src.synopsis_gen.http import safe_post

class LLMClient:
    def __init__(self):
        if not YANDEX_CLOUD_API_KEY or "PASTE_YOUR_API_KEY_HERE" in YANDEX_CLOUD_API_KEY:
            raise RuntimeError("Set YANDEX_CLOUD_API_KEY.")
        if not YANDEX_FOLDER_ID or "PASTE_YOUR_FOLDER_ID_HERE" in YANDEX_FOLDER_ID:
            raise RuntimeError("Set YANDEX_FOLDER_ID.")

    def chat(self, system: str, user: str, temperature: float = LLM_TEMPERATURE, max_tokens: int = LLM_MAX_TOKENS) -> str:
        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {"Authorization": f"Api-Key {YANDEX_CLOUD_API_KEY}", "Content-Type": "application/json"}
        model_uri = YANDEX_MODEL_URI_TEMPLATE.format(folder_id=YANDEX_FOLDER_ID)
        payload = {
            "modelUri": model_uri,
            "completionOptions": {"stream": False, "temperature": float(temperature), "maxTokens": int(max_tokens)},
            "messages": [{"role": "system", "text": system}, {"role": "user", "text": user}],
        }
        r = safe_post(url, headers=headers, payload=payload, timeout=190)
        if DEBUG and r.status_code != 200:
            print("Yandex response:", r.status_code, r.text[:2000])
        r.raise_for_status()
        data = r.json()
        alts = (data.get("result", {}) or {}).get("alternatives", []) or []
        return ((alts[0].get("message", {}) or {}).get("text", "") or "") if alts else ""