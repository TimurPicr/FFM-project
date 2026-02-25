import time
from typing import Dict, Optional
import requests

from .config import HTTP_TIMEOUT, HTTP_RETRIES, HTTP_BACKOFF, PUBMED_429_SLEEP, DEBUG

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "SynopsisRAG/FINAL (educational prototype)"})

def _sleep_backoff(attempt: int):
    time.sleep((HTTP_BACKOFF ** attempt) + 0.05)

def safe_get(url: str, timeout: int = HTTP_TIMEOUT) -> Optional[requests.Response]:
    for attempt in range(HTTP_RETRIES):
        try:
            r = SESSION.get(url, timeout=timeout)
            if r.status_code == 200 and (r.text or r.content):
                return r
            if DEBUG:
                print("GET failed:", r.status_code, url)
        except Exception as e:
            if DEBUG:
                print("GET exception:", str(e)[:200], url)
        _sleep_backoff(attempt)
    return None

def safe_post(url: str, headers: Dict, payload: Dict, timeout: int = 180) -> requests.Response:
    last_exc = None
    for attempt in range(HTTP_RETRIES):
        try:
            return SESSION.post(url, headers=headers, json=payload, timeout=timeout)
        except Exception as e:
            last_exc = e
            if DEBUG:
                print("POST exception:", str(e)[:200])
        _sleep_backoff(attempt)
    raise RuntimeError(f"POST failed after retries: {last_exc}")

def ncbi_get(url: str, params: Dict, timeout: int = 60) -> requests.Response:
    for attempt in range(HTTP_RETRIES + 4):
        r = SESSION.get(url, params=params, timeout=timeout)
        if r.status_code == 429:
            ra = r.headers.get("Retry-After")
            sleep_s = float(ra) if ra and ra.isdigit() else (PUBMED_429_SLEEP * (attempt + 1))
            if DEBUG:
                print(f"NCBI 429. Sleep {sleep_s:.1f}s and retry...")
            time.sleep(sleep_s)
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()
    return r