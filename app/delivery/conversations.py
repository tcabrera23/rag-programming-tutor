"""
CRUD de conversaciones: historial persistente en SQLite.
"""

import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.infra.database import SQLiteDatabase

router = APIRouter(prefix="/conversations", tags=["Conversations"])


def get_db() -> SQLiteDatabase:
    return SQLiteDatabase()


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    agent_name: str = "Wollok"
    model_name: str = "groq/compound"


class ConversationTitleUpdate(BaseModel):
    title: str


class MessageIn(BaseModel):
    role: str
    content: str
    has_attachment: bool = False
    attachment_type: Optional[str] = None


@router.get("")
def list_conversations(db: SQLiteDatabase = Depends(get_db)):
    return db.get_all_conversations()


@router.post("", status_code=201)
def create_conversation(
    body: ConversationCreate,
    db: SQLiteDatabase = Depends(get_db),
):
    conversation_id = f"conv_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    title = body.title or "Nueva conversación"
    ok = db.create_conversation(
        conversation_id=conversation_id,
        title=title,
        agent_name=body.agent_name,
        model_name=body.model_name,
    )
    if not ok:
        raise HTTPException(status_code=409, detail="Conversación ya existe.")
    return {"conversation_id": conversation_id, "title": title}


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: str,
    db: SQLiteDatabase = Depends(get_db),
):
    info = db.get_conversation_info(conversation_id)
    if not info:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
    messages = db.get_conversation_messages(conversation_id)
    return {**info, "messages": messages}


@router.patch("/{conversation_id}")
def update_conversation_title(
    conversation_id: str,
    body: ConversationTitleUpdate,
    db: SQLiteDatabase = Depends(get_db),
):
    ok = db.update_conversation_title(conversation_id, body.title)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
    return {"ok": True}


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str,
    db: SQLiteDatabase = Depends(get_db),
):
    db.delete_conversation(conversation_id)


@router.post("/{conversation_id}/messages", status_code=201)
def add_message(
    conversation_id: str,
    body: MessageIn,
    db: SQLiteDatabase = Depends(get_db),
):
    info = db.get_conversation_info(conversation_id)
    if not info:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
    db.add_message(
        conversation_id=conversation_id,
        role=body.role,
        content=body.content,
        has_attachment=body.has_attachment,
        attachment_type=body.attachment_type,
    )
    return {"ok": True}
