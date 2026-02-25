import os
import re
import json
from typing import List, Optional

import fitz
import faiss
from sentence_transformers import SentenceTransformer

from src.synopsis_gen.rag.mini_rag import MiniRAG, Chunk
from src.synopsis_gen.config import CACHE_DIR

def rag_cache_path(inn: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_\-]+", "_", inn.strip().lower())
    return os.path.join(CACHE_DIR, safe)

def save_rag(rag: MiniRAG, cache_dir: str):
    os.makedirs(cache_dir, exist_ok=True)
    faiss.write_index(rag.index, os.path.join(cache_dir, "faiss.index"))
    with open(os.path.join(cache_dir, "chunks.jsonl"), "w", encoding="utf-8") as f:
        for c in rag.chunks:
            f.write(json.dumps({"chunk_id": c.chunk_id, "text": c.text, "meta": c.meta}, ensure_ascii=False) + "\n")

def load_rag(cache_dir: str) -> Optional[MiniRAG]:
    idx_path = os.path.join(cache_dir, "faiss.index")
    ch_path = os.path.join(cache_dir, "chunks.jsonl")
    if not (os.path.exists(idx_path) and os.path.exists(ch_path)):
        return None
    rag = MiniRAG()
    rag.index = faiss.read_index(idx_path)
    chunks: List[Chunk] = []
    with open(ch_path, "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            chunks.append(Chunk(chunk_id=row["chunk_id"], text=row["text"], meta=row.get("meta") or {}))
    rag.chunks = chunks
    return rag