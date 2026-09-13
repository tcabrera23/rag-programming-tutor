"""
Tests de integración para flujos completos de la aplicación.
"""

import pytest
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.domain.agents import get_agent_config
from app.infra.rag import get_rag_instance
import os


class TestRAGIntegration:
    """Tests de integración para RAG."""

    def test_end_to_end_rag_flow_wollok(self, sample_wollok_query, database_url):
        """Test: Flujo completo RAG para Wollok."""
        if not os.getenv("OPENROUTER_API_KEY"):
            pytest.skip("OPENROUTER_API_KEY requerido")
        agent_config = get_agent_config("Wollok")
        rag = get_rag_instance()
        results = rag.search_theory(
            query=sample_wollok_query,
            table_name=agent_config["table"],
            query_name=agent_config["query_name"],
            match_count=3,
        )
        formatted = rag.format_results(results)
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        if "No se encontró" not in formatted:
            assert "# Teoría Recuperada" in formatted
            assert "Fragmento" in formatted
    
    def test_end_to_end_llm_response(self, sample_wollok_query, openrouter_api_key, database_url):
        """Test: Flujo completo con LLM."""
        # 1. Obtener config y buscar teoría
        agent_config = get_agent_config("Wollok")
        rag = get_rag_instance()
        
        results = rag.search_theory(
            query=sample_wollok_query,
            table_name=agent_config["table"],
            query_name=agent_config["query_name"],
            match_count=3
        )
        
        theory_context = rag.format_results(results)
        
        # 2. Crear LLM
        llm = ChatOpenAI(
            model="google/gemini-2.5-flash-lite",
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
            temperature=0.3
        )
        
        # 3. Preparar mensajes
        messages = [
            SystemMessage(content="Eres un tutor de Wollok. Responde brevemente."),
            HumanMessage(content=f"{sample_wollok_query}\n\nContexto:\n{theory_context}")
        ]
        
        # 4. Invocar LLM
        response = llm.invoke(messages)
        
        assert response is not None
        assert hasattr(response, 'content')
        assert len(response.content) > 0


class TestMultiAgentIntegration:
    """Tests de integración para múltiples agentes."""
    
    @pytest.mark.parametrize("agent_name,query", [
        ("Wollok", "¿Qué es un objeto?"),
        ("Haskell", "¿Qué son las funciones de orden superior?"),
        ("Prolog", "¿Qué es la unificación?")
    ])
    def test_all_agents_rag(self, agent_name, query, database_url):
        if not os.getenv("OPENROUTER_API_KEY"):
            pytest.skip("OPENROUTER_API_KEY requerido")
        agent_config = get_agent_config(agent_name)
        rag = get_rag_instance()
        
        results = rag.search_theory(
            query=query,
            table_name=agent_config["table"],
            query_name=agent_config["query_name"],
            match_count=2
        )
        
        # Verificar que la búsqueda no falle
        assert isinstance(results, list)


class TestPostgresConnection:
    """Tests de conexión a Postgres local."""

    def test_database_url_connects(self, database_url):
        import psycopg

        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM wollok")
                (n,) = cur.fetchone()
        assert n > 0

    def test_search_functions_exist(self, database_url):
        import psycopg

        test_embedding = "[" + ",".join(["0"] * 1536) + "]"
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                for fn in ("wollok_search", "haskell_search", "prolog_search"):
                    cur.execute(
                        f"SELECT * FROM {fn}(%s::vector, %s)",
                        (test_embedding, 1),
                    )
                    assert cur.fetchall() is not None

