"""
ChatPdeP FastAPI Service.
Expone el chat de agentes como API REST + endpoints compatibles con OpenAI.

Uso:
    uvicorn app.main:app --reload --port 8000

Cursor:
    Base URL : http://localhost:8000/v1
    Modelos  : chatpdep-wollok | chatpdep-haskell | chatpdep-prolog
"""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.delivery.agents import router as agents_router
from app.delivery.conversations import router as conv_router
from app.delivery.openai import router as openai_router

load_dotenv()

app = FastAPI(
    title="ChatPdeP API",
    description=(
        "Tutor de Paradigmas de Programación (UTN FRBA) — "
        "compatible con la API de OpenAI para integraciones con Cursor."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(openai_router)
app.include_router(conv_router)
app.include_router(agents_router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "chatpdep-api"}
