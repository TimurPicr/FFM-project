from typing import List, Dict, Optional
from tqdm import tqdm

from docx import Document
from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from src.synopsis_gen.text_utils import clean_final_text
from src.synopsis_gen.config import BIBLIO_LIMIT
from src.synopsis_gen.rag.mini_rag import MiniRAG

RED = RGBColor(0xC0, 0x00, 0x00)

def set_doc_styles(doc: Document):
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Times New Roman"
    font.size = Pt(12)

def add_title(doc: Document, text: str):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(16)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

def add_label_line(doc: Document, label: str, value: Optional[str], *, placeholder: Optional[str] = None):
    p = doc.add_paragraph()
    r1 = p.add_run(label + " ")
    r1.bold = True
    if value is not None and str(value).strip() != "":
        p.add_run(str(value))
    else:
        if placeholder is None:
            return
        r2 = p.add_run(placeholder)
        r2.font.color.rgb = RED

def add_heading(doc: Document, text: str, level: int = 1):
    doc.add_heading(text, level=level)

def add_text_block(doc: Document, text: str):
    text = clean_final_text(text)
    if not text:
        rr = doc.add_paragraph().add_run("НУЖНО УТОЧНИТЬ")
        rr.font.color.rgb = RED
        return
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            doc.add_paragraph("")
            continue
        if s.startswith(("-", "•", "*")):
            doc.add_paragraph(s.lstrip("-•* ").strip(), style="List Bullet")
        else:
            doc.add_paragraph(s)

def build_bibliography_from_rag(rag: MiniRAG, limit: int = BIBLIO_LIMIT) -> List[Dict]:
    bib, seen = [], set()
    def score(m: Dict) -> int:
        url = (m.get("url") or "").lower()
        src = (m.get("source") or "")
        s = 0
        if src == "SYNOPSIS_DOCX":
            s += 100
        if url.endswith(".pdf"):
            s += 40
        if "ema.europa.eu" in url:
            s += 35
        if "pmc.ncbi.nlm.nih.gov" in url:
            s += 25
        if "pubmed.ncbi.nlm.nih.gov" in url:
            s += 15
        return s
    metas = []
    for c in rag.chunks:
        m = c.meta or {}
        if m.get("url"):
            metas.append(m)
    metas.sort(key=score, reverse=True)
    for m in metas:
        url = m.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        bib.append({
            "id": str(m.get("id") or m.get("pmid") or m.get("pmcid") or ""),
            "title": str(m.get("title") or ""),
            "year": str(m.get("year") or ""),
            "url": str(url),
        })
        if len(bib) >= limit:
            break
    return bib

def render_docx(inn: str, meta: Dict, a: Dict, b: Dict, d: Dict, e: Dict, c: Dict, bibliography: List[Dict], out_path: str, sample_size_text: str):
    doc = Document()
    set_doc_styles(doc)

    add_title(doc, "СИНОПСИС ИССЛЕДОВАНИЯ")
    doc.add_paragraph("")

    add_label_line(doc, "Спонсор:", meta.get("sponsor"), placeholder="ВВЕДИТЕ СВОИ ДАННЫЕ")
    add_label_line(doc, "Название исследуемого препарата:", meta.get("test_product_name"), placeholder="ВВЕДИТЕ СВОИ ДАННЫЕ")
    add_label_line(doc, "Референтный препарат:", meta.get("reference_product_name"), placeholder="ВВЕДИТЕ СВОИ ДАННЫЕ")
    add_label_line(doc, "Действующее вещество:", inn)
    doc.add_paragraph("")

    add_label_line(doc, "Название исследования:", meta.get("study_title") or a.get("study_title"))
    add_label_line(doc, "Номер исследования:", meta.get("study_number"), placeholder="ВВЕДИТЕ СВОИ ДАННЫЕ")
    add_label_line(doc, "Фаза исследования:", a.get("phase") or "Биоэквивалентность / сравнительная фармакокинетика")
    add_label_line(doc, "Исследовательские центры:", meta.get("centers"), placeholder="ВВЕДИТЕ СВОИ ДАННЫЕ")
    doc.add_paragraph("")

    add_heading(doc, "Цели исследования", level=1)
    obj = a.get("objectives") or {}
    add_heading(doc, "Основная цель", level=2)
    add_text_block(doc, obj.get("primary") or "НУЖНО УТОЧНИТЬ")
    add_heading(doc, "Дополнительная цель", level=2)
    add_text_block(doc, obj.get("secondary") or "НУЖНО УТОЧНИТЬ")

    add_heading(doc, "Обоснование", level=1)
    add_text_block(doc, a.get("rationale", ""))

    add_heading(doc, "Профиль препарата", level=1)
    add_text_block(doc, a.get("drug_profile", ""))

    add_heading(doc, "Дизайн исследования", level=1)
    design = b.get("design") or {}
    for k, label in [
        ("type", "Тип/структура дизайна"),
        ("setting", "Условия проведения"),
        ("periods", "Периоды"),
        ("sequences", "Последовательности"),
        ("washout", "Отмывочный период"),
        ("randomization", "Рандомизация"),
        ("blinding", "Ослепление"),
        ("feeding", "Условия питания"),
        ("dose_admin", "Дозирование/введение"),
        ("endpoints", "Конечные точки/параметры"),
    ]:
        val = (design.get(k) or "").strip()
        add_label_line(doc, f"{label}:", val if val else None, placeholder="НУЖНО УТОЧНИТЬ")

    doc.add_paragraph("")
    add_heading(doc, "Исследуемая популяция и критерии отбора", level=1)
    add_text_block(doc, b.get("population", ""))

    add_heading(doc, "Критерии включения", level=2)
    inc = b.get("inclusion") or []
    if inc:
        for it in inc:
            doc.add_paragraph(str(it), style="List Bullet")
    else:
        rr = doc.add_paragraph().add_run("НУЖНО УТОЧНИТЬ")
        rr.font.color.rgb = RED

    add_heading(doc, "Критерии невключения", level=2)
    exc = b.get("exclusion") or []
    if exc:
        for it in exc:
            doc.add_paragraph(str(it), style="List Bullet")
    else:
        rr = doc.add_paragraph().add_run("НУЖНО УТОЧНИТЬ")
        rr.font.color.rgb = RED

    add_heading(doc, "Схема лечения / дозирование", level=1)
    add_text_block(doc, b.get("treatments", ""))

    add_heading(doc, "Краткий план процедур (резюме)", level=2)
    add_text_block(doc, b.get("schedule_brief", ""))

    add_heading(doc, "План процедур и график отбора проб", level=1)
    add_text_block(doc, d.get("schedule", ""))

    add_heading(doc, "Фармакокинетика и конечные точки", level=1)
    pkp = c.get("pk_parameters") or {}
    prim = pkp.get("primary") or ["AUC", "Cmax"]
    sec = pkp.get("secondary") or ["Tmax", "AUC0-∞", "t1/2 (если применимо)"]
    doc.add_paragraph("Первичные ФК-параметры:")
    for it in prim:
        doc.add_paragraph(str(it), style="List Bullet")
    doc.add_paragraph("Вторичные ФК-параметры:")
    for it in sec:
        doc.add_paragraph(str(it), style="List Bullet")

    add_heading(doc, "Биоаналитический раздел", level=1)
    add_text_block(doc, e.get("bioanalytics", ""))

    add_heading(doc, "Планируемые статистические методы", level=1)
    add_text_block(doc, e.get("statistics", ""))

    add_heading(doc, "Размер выборки", level=1)
    add_text_block(doc, sample_size_text)

    add_heading(doc, "Рандомизация", level=1)
    add_text_block(doc, c.get("randomization", ""))

    add_heading(doc, "Безопасность", level=1)
    add_text_block(doc, c.get("safety", ""))

    add_heading(doc, "Этика и регуляторные аспекты", level=1)
    add_text_block(doc, c.get("ethics", ""))

    add_heading(doc, "Управление данными и качество", level=1)
    add_text_block(doc, c.get("data_quality", ""))

    add_heading(doc, "Риски и ограничения", level=1)
    add_text_block(doc, c.get("risks_limits", ""))

    add_heading(doc, "Список литературы", level=1)
    if not bibliography:
        rr = doc.add_paragraph().add_run("НУЖНО УТОЧНИТЬ")
        rr.font.color.rgb = RED
    else:
        for i, b0 in enumerate(bibliography, 1):
            line = f"{i}. {b0.get('title','')} ({b0.get('year','')}). {b0.get('id','')} {b0.get('url','')}".strip()
            doc.add_paragraph(line)

    doc.save(out_path)
    return out_path