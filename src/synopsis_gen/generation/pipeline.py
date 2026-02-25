import os
import re
from typing import List, Dict, Optional
from tqdm import tqdm

from src.synopsis_gen.sources.pubmed import pubmed_search, pubmed_fetch_abstracts
from src.synopsis_gen.sources.europepmc import europepmc_search
from src.synopsis_gen.sources.fetchers import fetch_url_text
from src.synopsis_gen.sources.docx_ingest import docx_to_text
from src.synopsis_gen.rag.mini_rag import MiniRAG
from src.synopsis_gen.rag.cache import load_rag, save_rag
from src.synopsis_gen.rag.mini_rag import evidence_block
from src.synopsis_gen.llm.yandex_client import LLMClient
from src.synopsis_gen.generation.prompts import llm_part_a, llm_part_b_design, llm_part_d_schedule, llm_part_e_bio_stats, llm_part_c_safety
from src.synopsis_gen.generation.sample_size import be_sample_size_2x2, apply_dropout
from src.synopsis_gen.docx.render import render_docx, build_bibliography_from_rag
from src.synopsis_gen.text_utils import clean_final_text, short_hash
from src.synopsis_gen.config import PUBMED_RETMX, EUROPEPMC_PAGESIZE, MAX_PMC_FULLTEXT, MAX_URL_FULLTEXT, CACHE_DIR, DEBUG, TOP_K, BIBLIO_LIMIT

DEFAULT_SEED_URLS = {
    "palbociclib": [
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC11676693/",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC4613960/",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC7854954/",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC12322058/",
        "https://pubmed.ncbi.nlm.nih.gov/32799335/",
        "https://www.rlsnet.ru/active-substance/palbociklib-3641",
        "https://www.ema.europa.eu/en/documents/assessment-report/ibrance-epar-public-assessment-report_en.pdf",
    ],
    "nivolumab": [
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC6656473/",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC5270302/",
        "https://pubmed.ncbi.nlm.nih.gov/39317850/",
        "https://rls-ru.com/active-substance/nivolumab-3657",
        "https://bz.medvestnik.ru/classify/mnn/Nivolumab.html/description",
    ],
    "methotrexate": [
        "https://pubmed.ncbi.nlm.nih.gov/40090715/",
        "https://pubmed.ncbi.nlm.nih.gov/36484803/",
        "https://europepmc.org/article/med/1622413",
        "https://www.rlsnet.ru/active-substance/metotreksat-766",
        "https://pubmed.ncbi.nlm.nih.gov/27779157/",
    ],
}

def collect_corpus(inn: str, extra_urls: Optional[List[str]], local_synopsis_paths: List[str]) -> List[Dict]:
    inn_q = inn.strip()
    if not inn_q:
        return []

    pubmed_queries = [
        f'({inn_q}[Title/Abstract]) AND (pharmacokinetics OR absorption OR AUC OR Cmax OR Tmax OR "half-life")',
        f'({inn_q}[Title/Abstract]) AND (bioequivalence OR "relative bioavailability" OR "food effect")',
        f'({inn_q}[Title/Abstract]) AND (safety OR adverse events OR toxicity OR interaction)',
    ]
    pmids = []
    for q in pubmed_queries:
        pmids += pubmed_search(q, retmax=max(8, PUBMED_RETMX // 2))
    pmids = list(dict.fromkeys(pmids))[:PUBMED_RETMX]
    docs = pubmed_fetch_abstracts(pmids)

    ep_hits = []
    for q in [
        f'{inn_q} (pharmacokinetics OR absorption OR AUC OR Cmax OR Tmax OR "half-life")',
        f'{inn_q} (bioequivalence OR "food effect" OR "relative bioavailability")',
        f'{inn_q} (safety OR adverse events OR toxicity OR interaction)',
    ]:
        ep_hits += europepmc_search(q, page_size=max(10, EUROPEPMC_PAGESIZE // 2))

    seen = set()
    ep_uniq = []
    for d in ep_hits:
        key = (d.get("id",""), d.get("url",""))
        if key in seen:
            continue
        seen.add(key)
        ep_uniq.append(d)
    docs += ep_uniq

    pmc_urls = []
    for d in ep_uniq:
        pmcid = d.get("pmcid") or ""
        if pmcid:
            pmc_urls.append(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/")
    pmc_urls = list(dict.fromkeys(pmc_urls))[:MAX_PMC_FULLTEXT]
    for u in tqdm(pmc_urls, desc="Fetching PMC fulltext"):
        txt = fetch_url_text(u)
        if txt:
            docs.append({"source": "PMC", "id": short_hash(u), "title": f"PMC Fulltext: {u}", "year": "", "url": u, "text": txt})

    urls = []
    urls += DEFAULT_SEED_URLS.get(inn_q.lower(), [])
    if extra_urls:
        urls += extra_urls
    urls = list(dict.fromkeys([u.strip() for u in urls if u and u.strip()]))[:MAX_URL_FULLTEXT]
    for u in tqdm(urls, desc="Fetching seed URLs"):
        txt = fetch_url_text(u)
        if txt:
            docs.append({"source": "URL", "id": short_hash(u), "title": f"Source: {u}", "year": "", "url": u, "text": txt})

    for fp in local_synopsis_paths:
        if fp and os.path.exists(fp):
            txt = docx_to_text(fp)
            if txt:
                docs.append({
                    "source": "SYNOPSIS_DOCX",
                    "id": short_hash(fp),
                    "title": f"Эталонный синопсис: {os.path.basename(fp)}",
                    "year": "",
                    "url": fp,
                    "text": txt
                })

    uniq = {}
    for d in docs:
        key = (d.get("source",""), d.get("id",""), d.get("url",""))
        if key not in uniq and d.get("text"):
            uniq[key] = d
    return list(uniq.values())

# ==========================
# Pipeline
# ==========================
def build_or_load_rag(inn: str, extra_urls: Optional[List[str]], local_synopsis_paths: List[str], use_cache: bool = True) -> MiniRAG:
    cdir = os.path.join(CACHE_DIR, re.sub(r"[^a-zA-Z0-9_\-]+", "_", inn.strip().lower()))
    if use_cache:
        rag = load_rag(cdir)
        if rag is not None:
            if DEBUG:
                print("Loaded RAG cache:", cdir, "chunks:", len(rag.chunks))
            return rag
    corpus = collect_corpus(inn, extra_urls=extra_urls, local_synopsis_paths=local_synopsis_paths)
    rag = MiniRAG()
    rag.add_documents(corpus)
    if use_cache:
        save_rag(rag, cdir)
        if DEBUG:
            print("Saved RAG cache:", cdir)
    return rag

def generate_synopsis_docx(
    inn: str,
    indication: str,
    regimen: str,
    out_path: str,
    mode: str,
    sponsor: str = "",
    study_number: str = "",
    centers: str = "",
    test_product_name: str = "",
    reference_product_name: str = "",
    seed_urls: Optional[List[str]] = None,
    local_synopsis_paths: Optional[List[str]] = None,
    use_cache: bool = True,
    cvintra: float = 0.30,
    power: float = 0.80,
    alpha: float = 0.05,
    gmr: float = 0.95,
    dropout: float = 0.10,
) -> str:
    local_synopsis_paths = local_synopsis_paths or []
    rag = build_or_load_rag(inn, extra_urls=seed_urls, local_synopsis_paths=local_synopsis_paths, use_cache=use_cache)
    llm = LLMClient()

    ev_a = evidence_block(rag, f"{inn} {indication} {regimen} rationale pharmacokinetics absorption food effect interactions safety mechanism", top_k=TOP_K)
    ev_b = evidence_block(rag, f"{inn} {indication} {regimen} study design crossover 2x2 washout sequence TR RT randomization blinding fed fasted", top_k=TOP_K)
    ev_d = evidence_block(rag, f"{inn} {indication} {regimen} schedule visits procedures pharmacokinetics sampling timepoints hospitalization", top_k=TOP_K)
    ev_e = evidence_block(rag, f"{inn} {indication} {regimen} LC-MS/MS bioanalytical validation stability LLOQ statistics ANOVA TOST sample size CV", top_k=TOP_K)
    ev_c = evidence_block(rag, f"{inn} {indication} {regimen} safety adverse events monitoring labs ECG ethics GCP data quality monitoring risks", top_k=TOP_K)

    a = llm_part_a(llm, inn, indication, regimen, ev_a, mode=mode)
    b = llm_part_b_design(llm, inn, indication, regimen, ev_b, mode=mode)
    d = llm_part_d_schedule(llm, inn, indication, regimen, ev_d, mode=mode)
    e = llm_part_e_bio_stats(llm, inn, indication, regimen, ev_e, mode=mode)
    c = llm_part_c_safety(llm, inn, indication, regimen, ev_c, mode=mode)

    for k in ["rationale", "drug_profile", "study_title", "phase"]:
        if k in a:
            a[k] = clean_final_text(a.get(k, ""))
    if "objectives" in a and isinstance(a["objectives"], dict):
        for kk in ["primary", "secondary"]:
            a["objectives"][kk] = clean_final_text(a["objectives"].get(kk, ""))

    excl = b.get("exclusion") or []
    if not any("Несоответствие критериям включения" in str(x) for x in excl):
        excl.insert(0, "Несоответствие критериям включения")
    b["exclusion"] = excl

    if "design" in b and isinstance(b["design"], dict):
        for dk in list(b["design"].keys()):
            b["design"][dk] = clean_final_text(str(b["design"].get(dk, "")))
    b["population"] = clean_final_text(b.get("population", ""))
    b["treatments"] = clean_final_text(b.get("treatments", ""))
    b["schedule_brief"] = clean_final_text(b.get("schedule_brief", ""))

    d["schedule"] = clean_final_text(d.get("schedule", ""))
    e["bioanalytics"] = clean_final_text(e.get("bioanalytics", ""))
    e["statistics"] = clean_final_text(e.get("statistics", ""))
    e["sample_size_template"] = clean_final_text(e.get("sample_size_template", ""))

    c["randomization"] = clean_final_text(c.get("randomization", ""))
    c["safety"] = clean_final_text(c.get("safety", ""))
    c["ethics"] = clean_final_text(c.get("ethics", ""))
    c["data_quality"] = clean_final_text(c.get("data_quality", ""))
    c["risks_limits"] = clean_final_text(c.get("risks_limits", ""))

    if "pk_parameters" not in c or not c.get("pk_parameters"):
        c["pk_parameters"] = {"primary": ["AUC", "Cmax"], "secondary": ["Tmax", "AUC0-∞", "t1/2 (если применимо)"]}

    if mode == "be_fed":
        n0 = be_sample_size_2x2(cvintra, power=power, alpha=alpha, gmr=gmr)
        n = apply_dropout(n0, dropout=dropout)
        sample_size_text = f"""
{e.get("sample_size_template","")}

Численный расчет (2×2 перекрестный дизайн, TOST на лог-шкале):
- CVintra = {cvintra*100:.2f}%
- мощность = {power*100:.0f}%
- α = {alpha:.2f} (односторонний)
- ожидаемое отношение геометрических средних (GMR, T/R) = {gmr:.2f}
- учет выбывания (dropout) = {dropout*100:.0f}%

Требуемый размер выборки:
- расчетный минимум (без учета выбывания): {n0} участников
- планируемое число к рандомизации (с учетом выбывания): {n} участников
""".strip()
    else:
        sample_size_text = f"""
{e.get("sample_size_template","")}

НУЖНО УТОЧНИТЬ: выбранный дизайн (параллельный/перекрестный), целевая точность оценки ФК/проникновения в ЦНС,
допущения по вариабельности и допустимая ошибка (например, ≤5%) для расчета N.
""".strip()

    bib = build_bibliography_from_rag(rag, limit=BIBLIO_LIMIT)

    meta = {
        "sponsor": sponsor or "",
        "study_number": study_number or "",
        "centers": centers or "",
        "test_product_name": test_product_name or "",
        "reference_product_name": reference_product_name or "",
        "study_title": a.get("study_title") or "",
    }

    return render_docx(inn, meta, a, b, d, e, c, bib, out_path, sample_size_text)