import fitz
from docx import Document as DocxDocument
from typing import List, Dict

from src.synopsis_gen.text_utils import normalize_space
from src.synopsis_gen.http import SESSION
from src.synopsis_gen.config import HTTP_TIMEOUT, EUROPEPMC_PAGESIZE

def europepmc_search(query: str, page_size: int = EUROPEPMC_PAGESIZE) -> List[Dict]:
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {"query": query, "format": "json", "pageSize": str(page_size)}
    r = SESSION.get(url, params=params, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    hits = r.json().get("resultList", {}).get("result", []) or []
    out = []
    for h in hits:
        title = h.get("title", "") or ""
        abstract = h.get("abstractText", "") or ""
        year = h.get("pubYear", "") or ""
        pmid = h.get("pmid", "") or ""
        pmcid = h.get("pmcid", "") or ""
        url_ = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/" if pmcid else (f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "")
        out.append({
            "source": "EuropePMC",
            "id": pmcid or pmid or "",
            "title": title,
            "year": year,
            "url": url_,
            "pmcid": pmcid,
            "pmid": pmid,
            "text": normalize_space(f"{title}. {abstract}")
        })
    return out