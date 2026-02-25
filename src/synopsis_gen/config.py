import os

from dotenv import load_dotenv

load_dotenv()

YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY", "")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "")
YANDEX_MODEL_URI_TEMPLATE = os.getenv("YANDEX_MODEL_URI", "gpt://{folder_id}/yandexgpt/latest")

DEBUG = bool(int(os.getenv("DEBUG", "0")))

# RAG cache
CACHE_DIR = os.getenv("RAG_CACHE_DIR", ".rag_cache")

# RAG params
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "250"))
TOP_K = int(os.getenv("TOP_K", "22"))

# Corpus size
PUBMED_RETMX = int(os.getenv("PUBMED_RETMX", "24"))
EUROPEPMC_PAGESIZE = int(os.getenv("EUROPEPMC_PAGESIZE", "24"))
MAX_PMC_FULLTEXT = int(os.getenv("MAX_PMC_FULLTEXT", "8"))
MAX_URL_FULLTEXT = int(os.getenv("MAX_URL_FULLTEXT", "18"))
MAX_TEXT_CHARS = int(os.getenv("MAX_TEXT_CHARS", "240000"))

# NCBI
PUBMED_EFETCH_BATCH = int(os.getenv("PUBMED_EFETCH_BATCH", "10"))
PUBMED_MIN_DELAY = float(os.getenv("PUBMED_MIN_DELAY", "0.4"))
PUBMED_429_SLEEP = float(os.getenv("PUBMED_429_SLEEP", "3.0"))

# HTTP
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "45"))
HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "3"))
HTTP_BACKOFF = float(os.getenv("HTTP_BACKOFF", "1.5"))

# LLM
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.25"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "5200"))

# bibliography
BIBLIO_LIMIT = int(os.getenv("BIBLIO_LIMIT", "7"))