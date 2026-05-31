"""
Endpoints compatibles con la API de OpenAI.
Permite usar ChatPdeP directamente desde Cursor u otros clientes OpenAI.

Convención de nombres de modelos:
  chatpdep-wollok   → agente Wollok  (POO)
  chatpdep-haskell  → agente Haskell (Funcional)
  chatpdep-prolog   → agente Prolog  (Lógico)

Para seleccionar un modelo LLM específico, usa el formato:
  chatpdep-wollok:groq/compound
  chatpdep-haskell:openai/gpt-4o  (vía OpenRouter)
"""

import json
import time
import uuid
from typing import AsyncGenerator, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.services.chat_service import get_chat_service, ChatService
from config.agents import AGENTS

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])

_AGENT_PREFIX = "chatpdep-"
_DEFAULT_MODEL = "groq/compound"


def _parse_model(model: str) -> tuple[str, str]:
    """
    Devuelve (agent_name, llm_model_id).
    Soporta 'chatpdep-wollok' y 'chatpdep-wollok:groq/compound'.
    """
    if not model.startswith(_AGENT_PREFIX):
        # Intentar match directo con nombre de agente
        for name in AGENTS:
            if name.lower() == model.lower():
                return name, _DEFAULT_MODEL
        return "Wollok", _DEFAULT_MODEL

    rest = model[len(_AGENT_PREFIX):]
    if ":" in rest:
        agent_slug, llm_id = rest.split(":", 1)
    else:
        agent_slug, llm_id = rest, _DEFAULT_MODEL

    agent_name = next(
        (name for name in AGENTS if name.lower() == agent_slug.lower()),
        "Wollok",
    )
    return agent_name, llm_id


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


# ── Helpers SSE ────────────────────────────────────────────────────────────────

def _sse_chunk(completion_id: str, model: str, content: str) -> str:
    data = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
    }
    return f"data: {json.dumps(data)}\n\n"


def _sse_done(completion_id: str, model: str) -> str:
    data = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    return f"data: {json.dumps(data)}\n\ndata: [DONE]\n\n"


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/models")
def list_models():
    """Lista los modelos disponibles en formato OpenAI."""
    models = [
        {
            "id": f"{_AGENT_PREFIX}{name.lower()}",
            "object": "model",
            "created": 1700000000,
            "owned_by": "chatpdep",
            "description": f"Tutor de {name}",
        }
        for name in AGENTS
    ]
    return {"object": "list", "data": models}


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    service: ChatService = Depends(get_chat_service),
):
    """Endpoint de chat compatible con OpenAI. Soporta streaming."""
    agent_name, llm_model_id = _parse_model(request.model)

    # Separar historial del último mensaje del usuario
    chat_msgs = [m for m in request.messages if m.role in ("user", "assistant")]
    if not chat_msgs or chat_msgs[-1].role != "user":
        raise HTTPException(status_code=400, detail="El último mensaje debe ser del usuario.")

    user_message = chat_msgs[-1].content
    history = [{"role": m.role, "content": m.content} for m in chat_msgs[:-1]]

    if request.stream:
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

        def generate():
            for chunk_text in service.chat_stream(
                agent_name=agent_name,
                messages_history=history,
                user_message=user_message,
                model_id=llm_model_id,
            ):
                yield _sse_chunk(completion_id, request.model, chunk_text)
            yield _sse_done(completion_id, request.model)

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
