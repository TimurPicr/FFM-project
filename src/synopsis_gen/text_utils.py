import re
import hashlib
from typing import List

from .config import CHUNK_SIZE, CHUNK_OVERLAP

def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def short_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    text = normalize_space(text)
    if not text:
        return []
    chunks, i = [], 0
    step = max(1, chunk_size - overlap)
    while i < len(text):
        chunks.append(text[i:i+chunk_size])
        i += step
    return chunks

def clean_final_text(s: str) -> str:
    s = s or ""
    s = re.sub(r"\( *черновик *\)", "", s, flags=re.I)
    s = re.sub(r"\bчерновик\b", "", s, flags=re.I)
    s = re.sub(r"\bDraft\b", "", s, flags=re.I)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()