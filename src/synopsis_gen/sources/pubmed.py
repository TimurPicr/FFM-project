import fitz
from docx import Document as DocxDocument
from typing import List, Dict

import time
from bs4 import BeautifulSoup

from src.synopsis_gen.text_utils import normalize_space
from src.synopsis_gen.http import ncbi_get
from src.synopsis_gen.config import HTTP_TIMEOUT, PUBMED_RETMX, PUBMED_EFETCH_BATCH, PUBMED_MIN_DELAY

def pubmed_search(query: str, retmax: int = PUBMED_RETMX) -> List[str]:
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": str(retmax)}
    r = ncbi_get(url, params=params, timeout=HTTP_TIMEOUT)
    return r.json().get("esearchresult", {}).get("idlist", [])

def pubmed_fetch_abstracts(pmids: List[str]) -> List[Dict]:
    if not pmids:
        return []
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    out: List[Dict] = []
    for i in range(0, len(pmids), PUBMED_EFETCH_BATCH):
        batch = pmids[i:i+PUBMED_EFETCH_BATCH]
        params = {"db": "pubmed", "id": ",".join(batch), "retmode": "xml"}
        if i > 0:
            time.sleep(PUBMED_MIN_DELAY)
        r = ncbi_get(url, params=params, timeout=60)
        soup = BeautifulSoup(r.text, "lxml-xml")
        for art in soup.find_all("PubmedArticle"):
            pmid = art.find("PMID").get_text(strip=True) if art.find("PMID") else ""
            title = art.find("ArticleTitle").get_text(" ", strip=True) if art.find("ArticleTitle") else ""
            abs_tag = art.find("Abstract")
            abstract = abs_tag.get_text(" ", strip=True) if abs_tag else ""
            year = ""
            pubdate = art.find("PubDate")
            if pubdate and pubdate.find("Year"):
                year = pubdate.find("Year").get_text(strip=True)
            out.append({
                "source": "PubMed",
                "id": pmid,
                "title": title,
                "year": year,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                "text": normalize_space(f"{title}. {abstract}")
            })
    return out