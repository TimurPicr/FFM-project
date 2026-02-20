from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent  # папка, где лежит main.py

app = FastAPI()
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory="static"), name="static")



@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE_DIR / "index.html")

@app.get("/styles.css", include_in_schema=False)
def styles():
    return FileResponse(BASE_DIR / "styles.css", media_type="text/css")

@app.get("/search")
async def search(request: Request):
    q = request.query_params.get("q")
    q1 = request.query_params.get("q1")
    q2 = request.query_params.get("q2")
    q3 = request.query_params.get("q3")

    return templates.TemplateResponse("synopsis.html", {"request": request, "q": q, "q1" : q1, "q2" : q2, "q3": q3})