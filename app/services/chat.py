"""
Turno de chat: un solo camino para Streamlit y FastAPI.
"""

from dataclasses import dataclass
from typing import Dict, Generator, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.domain.agents import get_agent_config
from app.infra.llm import get_model_manager
from app.infra.rag import get_rag_instance
from app.services.classifier import QueryClassification, get_classifier


@dataclass
class TurnResult:
    content: str
    model_id: str
    is_fallback: bool = False
    fallback_reason: Optional[str] = None
    classification: Optional[QueryClassification] = None
    summarized: bool = False
    tokens_before: int = 0
    tokens_after: int = 0


def _count_tokens_approximate(messages: list) -> int:
    total_chars = sum(
        len(msg.content) if hasattr(msg, "content") else len(str(msg))
        for msg in messages
    )
    return total_chars // 4


def _summarize_conversation(llm, messages: list, keep_last: int = 4) -> list:
    if len(messages) <= keep_last + 2:
        return messages

    messages_to_summarize = messages[1:-keep_last]
    recent_messages = messages[-keep_last:]
    system_prompt = messages[0] if isinstance(messages[0], SystemMessage) else None

    if not messages_to_summarize:
        return messages

    conversation_text = "\n".join(
        f"{msg.__class__.__name__}: {msg.content}" for msg in messages_to_summarize
    )
    summary_prompt = (
        "Resume la siguiente conversación de manera concisa, preservando:\n"
        "- Conceptos clave discutidos\n"
        "- Código o ejemplos importantes mencionados\n"
        "- Conclusiones o decisiones tomadas\n\n"
        f"Conversación:\n{conversation_text}\n\nResumen:"
    )
    summary_response = llm.invoke([HumanMessage(content=summary_prompt)])
    summary_message = SystemMessage(
        content=f"Resumen de conversación previa: {summary_response.content}"
    )

    result = []
    if system_prompt:
        result.append(system_prompt)
    result.append(summary_message)
    result.extend(recent_messages)
    return result


def _build_langchain_messages(
    agent_config: dict,
    messages_history: List[Dict[str, str]],
    full_user_message: str,
    context_window: int,
    llm,
) -> tuple[list, bool, int, int]:
    rag = get_rag_instance()

    @tool
    def recuperar_teoria_agent(query: str) -> str:
        """Recupera teoría relevante sobre el lenguaje de programación."""
        results = rag.search_theory(
            query=query,
            table_name=agent_config["table"],
            query_name=agent_config["query_name"],
            match_count=5,
        )
        return rag.format_results(results)

    theory_context = recuperar_teoria_agent.invoke({"query": full_user_message})
    enriched_message = (
        f"Usuario: {full_user_message}\n\n"
        "--- Contexto de la base de conocimientos ---\n"
        f"{theory_context}\n\n"
        "Usa la información anterior para responder de manera precisa y fundamentada."
    )

    messages: list = [SystemMessage(content=agent_config["system_prompt"])]
    recent = (
        messages_history[-context_window:]
        if len(messages_history) > context_window
        else messages_history
    )
    for msg in recent:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=enriched_message))

    model_manager = get_model_manager()
    estimated_tokens = _count_tokens_approximate(messages)
    current_model_id = getattr(llm, "model_name", None) or getattr(llm, "model", None)
    current_model_cfg = (
        model_manager.get_model(current_model_id) if current_model_id else None
    )
    safe_limit = int(current_model_cfg.context_window * 0.8) if current_model_cfg else 25_000

    summarized = False
    tokens_before = estimated_tokens
    if estimated_tokens > safe_limit:
        messages = _summarize_conversation(llm, messages, keep_last=4)
        summarized = True
    return messages, summarized, tokens_before, _count_tokens_approximate(messages)


class ChatService:
    def __init__(self):
        self._model_manager = get_model_manager()

    def _resolve_model(
        self,
        model_id: str,
        user_message: str,
        auto_classify: bool,
        has_attachment: bool,
        provider: Optional[str] = None,
    ) -> tuple[str, Optional[QueryClassification]]:
        if not auto_classify:
            return model_id, None
        classifier = get_classifier()
        classification = classifier.classify(
            user_message, context={"has_attachment": has_attachment}
        )
        suggested = self._model_manager.suggest_model_by_tier(
            tier=classification.suggested_model_tier,
            provider=provider,
        )
        return suggested.id, classification

    def run_turn(
        self,
        agent_name: str,
        messages_history: List[Dict[str, str]],
        user_message: str,
        model_id: str = "groq/compound",
        context_window: int = 8,
        auto_classify: bool = False,
        attachment_content: Optional[str] = None,
        attachment_type: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> TurnResult:
        agent_config = get_agent_config(agent_name)
        full_message = user_message
        if attachment_content:
            full_message += f"\n\n--- Contenido del archivo adjunto ---\n{attachment_content}"

        final_model_id, classification = self._resolve_model(
            model_id,
            user_message,
            auto_classify,
            attachment_type is not None,
            provider,
        )
        llm, is_fallback, fallback_reason = self._model_manager.create_llm_with_fallback(
            model_id=final_model_id, temperature=0.5
        )
        messages, summarized, tokens_before, tokens_after = _build_langchain_messages(
            agent_config, messages_history, full_message, context_window, llm
        )
        response = llm.invoke(messages)
        return TurnResult(
            content=response.content,
            model_id=final_model_id,
            is_fallback=is_fallback,
            fallback_reason=fallback_reason,
            classification=classification,
            summarized=summarized,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
        )

    def chat(
        self,
        agent_name: str,
        messages_history: List[Dict[str, str]],
        user_message: str,
        model_id: str = "groq/compound",
        context_window: int = 8,
        auto_classify: bool = False,
        attachment_content: Optional[str] = None,
        attachment_type: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> str:
        return self.run_turn(
            agent_name=agent_name,
            messages_history=messages_history,
            user_message=user_message,
            model_id=model_id,
            context_window=context_window,
            auto_classify=auto_classify,
            attachment_content=attachment_content,
            attachment_type=attachment_type,
            provider=provider,
        ).content

    def chat_stream(
        self,
        agent_name: str,
        messages_history: List[Dict[str, str]],
        user_message: str,
        model_id: str = "groq/compound",
        context_window: int = 8,
        attachment_content: Optional[str] = None,
        attachment_type: Optional[str] = None,
    ) -> Generator[str, None, None]:
        agent_config = get_agent_config(agent_name)
        full_message = user_message
        if attachment_content:
            full_message += f"\n\n--- Contenido del archivo adjunto ---\n{attachment_content}"
        llm, _is_fallback, _reason = self._model_manager.create_llm_with_fallback(
            model_id=model_id, temperature=0.5
        )
        messages, _, _, _ = _build_langchain_messages(
            agent_config, messages_history, full_message, context_window, llm
        )
        for chunk in llm.stream(messages):
            if chunk.content:
                yield chunk.content


_service_instance: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    global _service_instance
    if _service_instance is None:
        _service_instance = ChatService()
    return _service_instance
