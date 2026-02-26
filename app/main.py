from __future__ import annotations

from pathlib import Path
from typing import List, Literal, Optional, Any

from fastapi import FastAPI, Request, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

from src.synopsis_gen.generation.pipeline import generate_synopsis_docx


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "../static"

app = FastAPI()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

class SynopsisRequest(BaseModel):
    inn: str = Field(description="INN/MNN")

    mode: Optional[Literal["be_fed", "cns_pk"]] = "be_fed"
    indication: Optional[str] = None
    regimen: Optional[str] = None
    out: Optional[str] = None

    sponsor: Optional[str] = None
    centers: Optional[str] = None
    test_product_name: Optional[str] = None
    reference_product_name: Optional[str] = None

    cvintra: Optional[float] = 0.30
    power: Optional[float] = 0.80
    alpha: Optional[float] = 0.05
    gmr: Optional[float] = 0.95
    dropout: Optional[float] = 0.10

    study_number: Optional[int] = None
    seed_url: Optional[List[str]] = None
    local_synopsis: Optional[List[str]] = None

    no_cache: Optional[bool] = False

    @field_validator("seed_url", "local_synopsis", mode="before")
    @classmethod
    def coerce_list(cls, v: Any):
        # из формы пустое поле приходит как ''
        if v is None or v == "":
            return []
        # иногда может прийти одиночная строка
        if isinstance(v, str):
            return [v]
        return v


def apply_mode_defaults(req: SynopsisRequest) -> SynopsisRequest:
    """Поведение как в CLI: если mode=cns_pk и пользователь не менял дефолты — подставить другие."""
    if req.mode == "cns_pk":
        default_indication = SynopsisRequest.model_fields["indication"].default
        default_regimen = SynopsisRequest.model_fields["regimen"].default

        if req.indication == default_indication:
            req.indication = (
                f"оценка фармакокинетики и экспозиции {req.inn} "
                f"при опухолях ЦНС (в т.ч. проникновение в ЦНС)"
            )
        if req.regimen == default_regimen:
            req.regimen = "без разницы"
    return req


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


@app.get("/styles.css", include_in_schema=False)
def styles() -> FileResponse:
    return FileResponse(BASE_DIR / "styles.css", media_type="text/css")


from typing import Optional
from fastapi import Query
from fastapi.responses import FileResponse, HTMLResponse

def to_int(v: Optional[str]) -> Optional[int]:
    if v is None or v.strip() == "":
        return None
    return int(v)

def to_float(v: Optional[str]) -> Optional[float]:
    if v is None or v.strip() == "":
        return None
    return float(v)

@app.get("/search")
async def search(
    inn: str,
    mode: str = "be_fed",
    indication: Optional[str] = None,
    regimen: Optional[str] = None,
    sponsor: Optional[str] = None,

    study_number: Optional[str] = None,   
    cvintra: Optional[str] = "0.30",      
    power: Optional[str] = "",            
    alpha: Optional[str] = "0.05",        
    gmr: Optional[str] = "",            
    dropout: Optional[str] = "",          

    centers: Optional[str] = None,
    test_product_name: Optional[str] = None,
    reference_product_name: Optional[str] = None,
    seed_url: Optional[str] = None,
    local_synopsis: Optional[str] = None,
    no_cache: Optional[int] = Query(default=0),
):
    req = SynopsisRequest(
        inn=inn,
        mode=mode,
        indication=indication,
        regimen=regimen,
        out="synopsis.docx",
        sponsor=sponsor,
        study_number=to_int(study_number),
        centers=centers,
        test_product_name=test_product_name,
        reference_product_name=reference_product_name,
        cvintra=to_float(cvintra) if cvintra not in (None, "") else 0.30,
        power=to_float(power) if power not in (None, "") else 0.80,
        alpha=to_float(alpha) if alpha not in (None, "") else 0.05,
        gmr=to_float(gmr) if gmr not in (None, "") else 0.95,
        dropout=to_float(dropout) if dropout not in (None, "") else 0.10,
        seed_url=seed_url,
        local_synopsis=local_synopsis,
        no_cache=no_cache,
    )
    req = apply_mode_defaults(req)

    out_path = await run_in_threadpool(
        generate_synopsis_docx,
        inn=req.inn,
        indication=req.indication,
        regimen=req.regimen,
        out_path=req.out,
        mode=req.mode,
        sponsor=req.sponsor,
        study_number=req.study_number,
        centers=req.centers,
        test_product_name=req.test_product_name,
        reference_product_name=req.reference_product_name,
        seed_urls=req.seed_url or None,
        local_synopsis_paths=req.local_synopsis,
        use_cache=(not req.no_cache),
        cvintra=req.cvintra,
        power=req.power,
        alpha=req.alpha,
        gmr=req.gmr,
        dropout=req.dropout,
    )

    return FileResponse(
        path=local_synopsis / "synopsis.docx",
        filename="synopsis.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )