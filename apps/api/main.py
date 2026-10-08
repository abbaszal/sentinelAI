from fastapi import FastAPI

from config import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "message": "Welcome to SentinelAI",
    }


@app.get("/v1/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }