from typing import Optional
from bs4 import BeautifulSoup
import fitz
from docx import Document as DocxDocument

from src.synopsis_gen.text_utils import normalize_space
from src.synopsis_gen.http import safe_get
from src.synopsis_gen.config import HTTP_TIMEOUT, MAX_TEXT_CHARS

def pmc_fetch_fulltext(pmc_url: str, max_chars: int = MAX_TEXT_CHARS) -> Optional[str]:
    r = safe_get(pmc_url, timeout=HTTP_TIMEOUT)
    if not r:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    main = soup.find("article") or soup
    for tag in main(["script", "style", "noscript"]):
        tag.decompose()
    text = normalize_space(main.get_text(" ", strip=True))
    return (text[:max_chars] if max_chars and len(text) > max_chars else text) or None

def fetch_url_text(url: str, max_chars: int = MAX_TEXT_CHARS) -> Optional[str]:
    if "pmc.ncbi.nlm.nih.gov/articles/" in url:
        txt = pmc_fetch_fulltext(url, max_chars=max_chars)
        if txt:
            return txt
    if url.lower().endswith(".pdf"):
        r = safe_get(url, timeout=70)
        if not r:
            return None
        try:
            doc = fitz.open(stream=r.content, filetype="pdf")
            parts = []
            for i in range(min(doc.page_count, 30)):
                parts.append(doc.load_page(i).get_text("text"))
            text = normalize_space(" ".join(parts))
            return (text[:max_chars] if max_chars and len(text) > max_chars else text) or None
        except Exception:
            return None
    r = safe_get(url, timeout=HTTP_TIMEOUT)
    if not r:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = normalize_space(soup.get_text(" ", strip=True))
    return (text[:max_chars] if max_chars and len(text) > max_chars else text) or None