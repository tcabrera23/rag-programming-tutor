"""
Tests unitarios para el módulo RAG (app/infra/rag.py).
"""

import os

import pytest

from app.infra.rag import PostgresRAG, get_rag_instance


@pytest.fixture
def rag_ready():
    if not os.getenv("DATABASE_URL") or not os.getenv("OPENROUTER_API_KEY"):
        pytest.skip("DATABASE_URL y OPENROUTER_API_KEY requeridos para RAG.")


class TestPostgresRAG:
    def test_rejects_unknown_table(self, monkeypatch, database_url):
        monkeypatch.setenv("DATABASE_URL", database_url)
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-not-used")
        rag = PostgresRAG()
        with pytest.raises(ValueError, match="no permitida"):
            rag.search_theory("x", table_name="leads", query_name="leads_search")

    def test_rejects_mismatched_query_name(self, monkeypatch, database_url):
        monkeypatch.setenv("DATABASE_URL", database_url)
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-not-used")
        rag = PostgresRAG()
        with pytest.raises(ValueError, match="no permitida"):
            rag.search_theory("x", table_name="wollok", query_name="haskell_search")

    def test_search_theory_wollok(self, rag_ready, sample_wollok_query):
        rag = get_rag_instance()
        results = rag.search_theory(
            query=sample_wollok_query,
            table_name="wollok",
            query_name="wollok_search",
            match_count=3,
        )
        assert isinstance(results, list)
        if results:
            assert len(results) <= 3
            assert "content" in results[0]
            assert "similarity" in results[0]
            assert "metadata" in results[0]

    def test_search_theory_haskell(self, rag_ready, sample_haskell_query):
        rag = get_rag_instance()
        results = rag.search_theory(
            query=sample_haskell_query,
            table_name="haskell",
            query_name="haskell_search",
            match_count=3,
        )
        assert isinstance(results, list)
        if results:
            assert len(results) <= 3

    def test_search_theory_prolog(self, rag_ready, sample_prolog_query):
        rag = get_rag_instance()
        results = rag.search_theory(
            query=sample_prolog_query,
            table_name="prolog",
            query_name="prolog_search",
            match_count=3,
        )
        assert isinstance(results, list)
        if results:
            assert len(results) <= 3

    def test_format_results_empty(self):
        formatted = PostgresRAG.format_results([])
        assert "No se encontró información relevante" in formatted

    def test_format_results_with_data(self):
        formatted = PostgresRAG.format_results(
            [
                {
                    "content": "Un objeto en Wollok encapsula estado y comportamiento.",
                    "similarity": 0.85,
                    "metadata": {"source": "Guía de Wollok"},
                }
            ]
        )
        assert "# Teoría Recuperada" in formatted
        assert "Fragmento 1" in formatted
        assert "0.850" in formatted
        assert "Guía de Wollok" in formatted


class TestRecuperarTeoriaTool:
    def test_recuperar_teoria_basic(self, rag_ready, sample_wollok_query):
        from app.domain.tools import recuperar_teoria

        result = recuperar_teoria.invoke({"query": sample_wollok_query})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_recuperar_teoria_with_config(self, rag_ready, sample_haskell_query, agent_configs):
        from app.domain.tools import recuperar_teoria

        haskell_config = agent_configs["Haskell"]
        result = recuperar_teoria.invoke(
            {"query": sample_haskell_query, "agent_config": haskell_config}
        )
        assert isinstance(result, str)
        assert len(result) > 0
