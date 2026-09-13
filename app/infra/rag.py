"""
Cliente RAG contra Postgres + pgvector.
"""

import json
import os
from typing import Any, Dict, List, Optional

import psycopg
from langchain_openai import OpenAIEmbeddings
from psycopg.rows import dict_row

_TABLES = frozenset({"wollok", "haskell", "prolog"})
_SEARCH_SQL = {
    "wollok": "SELECT id, content, metadata, similarity FROM wollok_search(%s::vector, %s, %s::jsonb)",
    "haskell": "SELECT id, content, metadata, similarity FROM haskell_search(%s::vector, %s, %s::jsonb)",
    "prolog": "SELECT id, content, metadata, similarity FROM prolog_search(%s::vector, %s, %s::jsonb)",
}


def _vector_literal(values: List[float]) -> str:
    return "[" + ",".join(str(float(x)) for x in values) + "]"


class PostgresRAG:
    """Búsqueda semántica en las tablas de teoría locales."""

    def __init__(self):
        self.database_url = os.environ.get("DATABASE_URL")
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL debe estar configurado "
                "(ej: postgresql://chatpdep:chatpdep@localhost:5432/chatpdep)"
            )

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
        table = (table_name or "").lower()
        if table not in _TABLES:
            raise ValueError(f"Tabla RAG no permitida: {table_name}")
        expected_fn = f"{table}_search"
        if query_name and query_name != expected_fn:
            raise ValueError(f"Función RAG no permitida: {query_name}")

        try:
            query_embedding = self.embeddings.embed_query(query)
            filt = json.dumps(filter_metadata or {}, ensure_ascii=False)
            sql = _SEARCH_SQL[table]
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, (_vector_literal(query_embedding), match_count, filt))
                    rows = cur.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"Error en búsqueda RAG: {e}")
            return []

    @staticmethod
    def format_results(results: List[Dict[str, Any]]) -> str:
        if not results:
            return "No se encontró información relevante en la base de conocimientos."

        formatted = "# Teoría Recuperada\n\n"
        for i, doc in enumerate(results, 1):
            content = doc.get("content", "")
            similarity = doc.get("similarity", 0) or 0
            metadata = doc.get("metadata") or {}
            formatted += f"## Fragmento {i} (Similitud: {similarity:.3f})\n"
            if isinstance(metadata, dict):
                source = metadata.get("source", "")
                if source:
                    formatted += f"**Fuente:** {source}\n\n"
            formatted += f"{content}\n\n"
            formatted += "---\n\n"
        return formatted


_rag_instance: Optional[PostgresRAG] = None


def get_rag_instance() -> PostgresRAG:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = PostgresRAG()
    return _rag_instance
