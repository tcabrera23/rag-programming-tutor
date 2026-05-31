"""
Endpoints compatibles con la API de OpenAI.

── Modo A: base URL por agente (RECOMENDADO para Cursor) ─────────────────────
  Configurá en Cursor tres "proveedores" separados:

  Agente Wollok  → Base URL: http://localhost:8000/v1/wollok
  Agente Haskell → Base URL: http://localhost:8000/v1/haskell
  Agente Prolog  → Base URL: http://localhost:8000/v1/prolog

  Cursor llamará a:
    GET  /v1/{agente}/models              → lista los LLMs disponibles
    POST /v1/{agente}/chat/completions    → el campo "model" es el ID del LLM
                                            (ej: "groq/compound", "openai/gpt-4o")

── Modo B: un único proveedor con agente+LLM en el nombre de modelo ──────────
  Base URL: http://localhost:8000/v1
  Modelos : chatpdep-wollok | chatpdep-haskell | chatpdep-prolog
            chatpdep-wollok:groq/compound  (agente:LLM)
"""

import json
import time
import uuid
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.services.chat_service import get_chat_service, ChatService
from config.agents import AGENTS
from utils.model_manager import get_model_manager

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])

_AGENT_PREFIX = "chatpdep-"
_DEFAULT_LLM = "groq/compound"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _resolve_agent(slug: str) -> str:
    """Devuelve el nombre canónico del agente o 'Wollok' como fallback."""
    return next(
        (name for name in AGENTS if name.lower() == slug.lower()),
        "Wollok",
    )


def _parse_model_field(model: str) -> tuple[str, str]:
    """
    Modo B: extrae (agent_name, llm_id) del campo model del request.
    Soporta 'chatpdep-wollok' y 'chatpdep-wollok:groq/compound'.
    """
    if not model.startswith(_AGENT_PREFIX):
        return _resolve_agent(model), _DEFAULT_LLM

    rest = model[len(_AGENT_PREFIX):]
    if ":" in rest:
        agent_slug, llm_id = rest.split(":", 1)
    else:
        agent_slug, llm_id = rest, _DEFAULT_LLM

    return _resolve_agent(agent_slug), llm_id


def _llm_models_list(agent_name: str) -> list:
    """Lista los LLMs disponibles en formato OpenAI model object."""
    mm = get_model_manager()
    all_models = (
        list(mm.PREDEFINED_MODELS.values())
        + mm.GROQ_MODELS
        + mm.SUGGESTED_LOCAL_MODELS
        + list(mm.custom_models.values())
    )
    return [
        {
            "id": m.id,
            "object": "model",
            "created": 1700000000,
            "owned_by": m.provider,
            "description": m.description,
            "tier": m.tier,
            "input_cost": m.input_cost,
            "output_cost": m.output_cost,
        }
        for m in all_models
    ]


def _sse_chunk(cid: str, model: str, content: str) -> str:
    data = {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
    }
    return f"data: {json.dumps(data)}\n\n"


def _sse_done(cid: str, model: str) -> str:
    data = {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    return f"data: {json.dumps(data)}\n\ndata: [DONE]\n\n"


# ── Schemas ────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = 0.5
    max_tokens: Optional[int] = None


def _extract_history_and_message(
    messages: List[ChatMessage],
) -> tuple[str, list]:
    chat_msgs = [m for m in messages if m.role in ("user", "assistant")]
    if not chat_msgs or chat_msgs[-1].role != "user":
        raise HTTPException(
            status_code=400, detail="El último mensaje debe ser del usuario."
        )
    user_message = chat_msgs[-1].content
    history = [{"role": m.role, "content": m.content} for m in chat_msgs[:-1]]
    return user_message, history


def _run_chat(
    service: ChatService,
    request: ChatCompletionRequest,
    agent_name: str,
    llm_model_id: str,
):
    user_message, history = _extract_history_and_message(request.messages)

    if request.stream:
        cid = f"chatcmpl-{uuid.uuid4().hex[:8]}"

        def generate():
            for chunk in service.chat_stream(
                agent_name=agent_name,
                messages_history=history,
                user_message=user_message,
                model_id=llm_model_id,
            ):
                yield _sse_chunk(cid, request.model, chunk)
            yield _sse_done(cid, request.model)

        return StreamingResponse(generate(), media_type="text/event-stream")

    response_text = service.chat(
        agent_name=agent_name,
        messages_history=history,
        user_message=user_message,
        model_id=llm_model_id,
    )
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": -1, "completion_tokens": -1, "total_tokens": -1},
    }


# ── Modo A: base URL por agente (/v1/{agent_name}/*) ──────────────────────────

@router.get("/{agent_slug}/models")
def agent_models(agent_slug: str):
    """
    Lista los LLMs disponibles para un agente.
    Cursor muestra estos modelos en el selector para elegir el LLM.

    Ejemplos:
      GET /v1/wollok/models
      GET /v1/haskell/models
    """
    agent_name = _resolve_agent(agent_slug)
    if agent_name not in AGENTS and agent_slug.capitalize() not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_slug}' no encontrado.")
    return {"object": "list", "data": _llm_models_list(agent_name)}


@router.post("/{agent_slug}/chat/completions")
def agent_chat_completions(
    agent_slug: str,
    request: ChatCompletionRequest,
    service: ChatService = Depends(get_chat_service),
):
    """
    Chat con un agente específico. El campo 'model' del request es el LLM a usar.

    Ejemplos:
      POST /v1/wollok/chat/completions   body: {"model": "groq/compound", ...}
      POST /v1/haskell/chat/completions  body: {"model": "openai/gpt-4o", ...}
    """
    agent_name = _resolve_agent(agent_slug)
    llm_model_id = request.model or _DEFAULT_LLM
    return _run_chat(service, request, agent_name, llm_model_id)


# ── Modo B: un único proveedor (/v1/*) ────────────────────────────────────────

@router.get("/models")
def list_models():
    """
    Lista los agentes disponibles como modelos OpenAI (Modo B).
    Base URL: http://localhost:8000/v1
    """
    models = [
        {
            "id": f"{_AGENT_PREFIX}{name.lower()}",
            "object": "model",
            "created": 1700000000,
            "owned_by": "chatpdep",
            "description": f"Tutor de {name} — usa 'chatpdep-{name.lower()}:llm-id' para elegir LLM",
        }
        for name in AGENTS
    ]
    return {"object": "list", "data": models}


@router.post("/chat/completions")
def chat_completions(
    request: ChatCompletionRequest,
    service: ChatService = Depends(get_chat_service),
):
    """Chat con agente+LLM codificados en el nombre del modelo (Modo B)."""
    agent_name, llm_model_id = _parse_model_field(request.model)
    return _run_chat(service, request, agent_name, llm_model_id)
