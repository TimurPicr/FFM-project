from docx import Document as DocxDocument

from src.synopsis_gen.text_utils import normalize_space

def docx_to_text(path: str, max_chars: int = 250_000) -> str:
    d = DocxDocument(path)
    parts = []
    for p in d.paragraphs:
        t = (p.text or "").strip()
        if t:
            parts.append(t)
    text = "\n".join(parts)
    text = normalize_space(text)
    return text[:max_chars]