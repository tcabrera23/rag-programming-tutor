"""
Registro de métricas de uso en Supabase (tabla chatpdep_tokens).
"""

import os
from datetime import datetime
from typing import Optional

from supabase import Client, create_client


class MetricsTracker:
    def __init__(self):
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get(
            "SUPABASE_SERVICE_KEY"
        )
        if not self.supabase_url or not self.supabase_key:
            self.supabase = None
            print("⚠️  SUPABASE_URL y SUPABASE_ANON_KEY no configurados. Tracking deshabilitado.")
        else:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

    def log_interaction(
        self,
        conversation_id: str,
        user_input: str,
        agent_response: str,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        llm_latency_ms: Optional[int] = None,
        workflow_duration_ms: Optional[int] = None,
        agent_name: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> bool:
        if not self.supabase:
            return False
        try:
            tokens_total = None
            if tokens_in is not None and tokens_out is not None:
                tokens_total = tokens_in + tokens_out
            data = {
                "conversation_id": conversation_id,
                "user_input": user_input,
                "agent_response": agent_response,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "tokens_total": tokens_total,
                "llm_api_latency_ms": llm_latency_ms,
                "workflow_duration_ms": workflow_duration_ms,
                "timestamp": datetime.utcnow().isoformat(),
                "n8n_workflow_name": agent_name,
                "n8n_workflow_id": model_name,
            }
            self.supabase.table("chatpdep_tokens").insert(data).execute()
            return True
        except Exception as e:
            print(f"⚠️  Error al registrar métrica: {e}")
            return False


_tracker_instance = None


def get_tracker() -> MetricsTracker:
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = MetricsTracker()
    return _tracker_instance


def log_interaction(
    conversation_id: str,
    user_input: str,
    agent_response: str,
    **kwargs,
) -> bool:
    return get_tracker().log_interaction(
        conversation_id=conversation_id,
        user_input=user_input,
        agent_response=agent_response,
        **kwargs,
    )
