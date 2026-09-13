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
    
    def test_end_to_end_rag_flow_wollok(self, sample_wollok_query):
        """Test: Flujo completo RAG para Wollok."""
        # 1. Obtener configuración
        agent_config = get_agent_config("Wollok")
        
        # 2. Buscar teoría
        rag = get_rag_instance()
        results = rag.search_theory(
            query=sample_wollok_query,
            table_name=agent_config["table"],
            query_name=agent_config["query_name"],
            match_count=3
        )
        
        # 3. Formatear resultados
        formatted = rag.format_results(results)
        
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        
        # Si hay resultados, verificar formato
        if "No se encontró" not in formatted:
            assert "# Teoría Recuperada" in formatted
            assert "Fragmento" in formatted
    
    def test_end_to_end_llm_response(self, sample_wollok_query, openrouter_api_key):
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
    def test_all_agents_rag(self, agent_name, query):
        """Test: Verificar que RAG funciona para todos los agentes."""
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


class TestSupabaseConnection:
    """Tests de conexión a Supabase."""
    
    def test_supabase_connection(self, supabase_config):
        """Test: Verificar conexión a Supabase."""
        from supabase import create_client
        
        supabase = create_client(
            supabase_config["url"],
            supabase_config["key"]
        )
        
        assert supabase is not None
    
    def test_supabase_rpc_functions_exist(self, supabase_config):
        """Test: Verificar que las funciones RPC existan."""
        from supabase import create_client
        
        supabase = create_client(
            supabase_config["url"],
            supabase_config["key"]
        )
        
        # Crear un embedding de prueba (vector de 1536 ceros)
        test_embedding = [0.0] * 1536
        
        # Intentar llamar cada función RPC
        rpc_functions = ["wollok_search", "haskell_search", "prolog_search"]
        
        for func_name in rpc_functions:
            try:
                response = supabase.rpc(
                    func_name,
                    {
                        "query_embedding": test_embedding,
                        "match_count": 1
                    }
                ).execute()
                
                # Si no falla, la función existe
                assert response is not None
            except Exception as e:
                pytest.fail(f"RPC function {func_name} no disponible: {e}")

