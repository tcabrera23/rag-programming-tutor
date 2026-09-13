"""
Cliente RAG contra Supabase (pgvector).
"""

import os
from typing import Any, Dict, List, Optional

from langchain_openai import OpenAIEmbeddings
from supabase import Client, create_client


class SupabaseRAG:
    """Búsqueda semántica en las tablas de teoría."""

    def __init__(self):
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get(
            "SUPABASE_SERVICE_KEY"
        )

        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "SUPABASE_URL y SUPABASE_ANON_KEY (o SUPABASE_SERVICE_KEY para retrocompatibilidad) "
                "deben estar configurados en las variables de entorno"
            )

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            raise ValueError(
                "OPENROUTER_API_KEY debe estar configurado en las variables de entorno"
            )

        self.embeddings = OpenAIEmbeddings(
            openai_api_key=openrouter_api_key,
            model="openai/text-embedding-3-small",
            base_url="https://openrouter.ai/api/v1",
        )

    def search_theory(
        self,
        query: str,
        table_name: str,
        query_name: str,
        match_count: int = 5,
        filter_metadata: dict = None,
    ) -> List[Dict[str, Any]]:
        try:
            query_embedding = self.embeddings.embed_query(query)
            rpc_params = {
                "query_embedding": query_embedding,
                "match_count": match_count,
            }
            if filter_metadata:
                rpc_params["filter"] = filter_metadata
            response = self.supabase.rpc(query_name, rpc_params).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error en búsqueda RAG: {e}")
            return []

    def format_results(self, results: List[Dict[str, Any]]) -> str:
        if not results:
            return "No se encontró información relevante en la base de conocimientos."

        formatted = "# Teoría Recuperada\n\n"
        for i, doc in enumerate(results, 1):
            content = doc.get("content", "")
            similarity = doc.get("similarity", 0)
            metadata = doc.get("metadata", {})
            formatted += f"## Fragmento {i} (Similitud: {similarity:.3f})\n"
            if metadata:
                source = metadata.get("source", "")
                if source:
                    formatted += f"**Fuente:** {source}\n\n"
            formatted += f"{content}\n\n"
            formatted += "---\n\n"
        return formatted


_rag_instance: Optional[SupabaseRAG] = None


def get_rag_instance() -> SupabaseRAG:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = SupabaseRAG()
    return _rag_instance
