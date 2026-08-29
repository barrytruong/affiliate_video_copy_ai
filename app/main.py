import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, settings
from app.ollama_client import check_ollama_health
from app.routes import api, pages

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        check_ollama_health(settings.ollama_host, settings.ollama_model)
        logger.info("Ollama reachable, model '%s' available.", settings.ollama_model)
    except Exception as e:
        logger.warning("Ollama health check failed at startup: %s", e)
    yield


app = FastAPI(title="Affiliate Video Script Writer", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
app.include_router(pages.router)
app.include_router(api.router)
