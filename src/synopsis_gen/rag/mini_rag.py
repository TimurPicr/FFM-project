from dataclasses import dataclass
from typing import List, Dict
from tqdm import tqdm

import fitz
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from src.synopsis_gen.text_utils import short_hash, chunk_text
from src.synopsis_gen.config import EMBED_MODEL_NAME, TOP_K

@dataclass
class Chunk:
    chunk_id: str
    text: str
    meta: Dict

class MiniRAG:
    def __init__(self, embed_model_name: str = EMBED_MODEL_NAME):
        self.model = SentenceTransformer(embed_model_name)
        self.index = None
        self.chunks: List[Chunk] = []
        self.dim = None

    def add_documents(self, docs: List[Dict]):
        new_chunks: List[Chunk] = []
        for d in docs:
            text = d.get("text", "")
            if not text:
                continue
            for i, ch in enumerate(chunk_text(text)):
                cid = f"{d.get('source','src')}-{d.get('id','')}-{i}-{short_hash(ch)}"
                meta = {k: d.get(k) for k in ["source", "id", "title", "year", "url", "pmid", "pmcid"] if d.get(k) is not None}
                new_chunks.append(Chunk(chunk_id=cid, text=ch, meta=meta))
        if not new_chunks:
            return
        emb = self.model.encode([c.text for c in new_chunks], show_progress_bar=True, normalize_embeddings=True)
        emb = np.asarray(emb, dtype="float32")
        if self.index is None:
            self.dim = emb.shape[1]
            self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(emb)
        self.chunks.extend(new_chunks)

    def search(self, query: str, top_k: int = TOP_K) -> List[Chunk]:
        if self.index is None or not self.chunks:
            return []
        q = self.model.encode([query], normalize_embeddings=True)
        q = np.asarray(q, dtype="float32")
        _, idxs = self.index.search(q, top_k)
        idxs = idxs[0].tolist()
        return [self.chunks[ix] for ix in idxs if 0 <= ix < len(self.chunks)]

def evidence_block(rag: MiniRAG, query: str, top_k: int = TOP_K) -> str:
    chunks = rag.search(query, top_k=top_k)
    lines, seen = [], set()
    for c in chunks:
        m = c.meta or {}
        key = (m.get("source",""), m.get("id",""), m.get("url",""))
        if key in seen:
            continue
        seen.add(key)
        sid = m.get("id") or m.get("pmid") or m.get("pmcid") or ""
        label = f"[{m.get('source','SRC')}|{sid}|{m.get('year','')}] {m.get('url','')}"
        lines.append(f"{label}\nSNIPPET: {c.text}\n")
    return "\n---\n".join(lines) if lines else "НЕТ ДОКАЗАТЕЛЬСТВ"