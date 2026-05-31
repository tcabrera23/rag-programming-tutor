"""
ChatPdeP FastAPI Service.
Expone el chat de agentes como API REST + endpoints compatibles con OpenAI
para integraciones con Cursor, VS Code, etc.

Uso rápido:
    uvicorn api.main:app --reload --port 8000

Configuración Cursor:
    Base URL : http://localhost:8000/v1
    Modelos  : chatpdep-wollok | chatpdep-haskell | chatpdep-prolog
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

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

# Routers
from api.routes.openai import router as openai_router
from api.routes.conversations import router as conv_router
from api.routes.agents import router as agents_router

app.include_router(openai_router)
app.include_router(conv_router)
app.include_router(agents_router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "chatpdep-api"}
