"""
Tests unitarios para el módulo RAG (app/infra/rag.py).
"""

import pytest
from app.domain.tools import recuperar_teoria
from app.infra.rag import SupabaseRAG, get_rag_instance


class TestSupabaseRAG:
    """Tests para la clase SupabaseRAG."""
    
    def test_rag_instance_creation(self, supabase_config):
        """Test: Crear instancia de SupabaseRAG."""
        rag = SupabaseRAG()
        
        assert rag.supabase is not None
        assert rag.embeddings is not None
        assert rag.supabase_url == supabase_config["url"]
        assert rag.supabase_key == supabase_config["key"]
    
    def test_singleton_pattern(self):
        """Test: Verificar que get_rag_instance retorna la misma instancia."""
        instance1 = get_rag_instance()
        instance2 = get_rag_instance()
        
        assert instance1 is instance2
    
    def test_search_theory_wollok(self, sample_wollok_query):
        """Test: Buscar teoría en tabla Wollok."""
        rag = get_rag_instance()
        
        results = rag.search_theory(
            query=sample_wollok_query,
            table_name="wollok",
            query_name="wollok_search",
            match_count=3
        )
        
        assert isinstance(results, list)
        # Verificar que retorne resultados (si la tabla tiene datos)
        if results:
            assert len(results) <= 3
            assert "content" in results[0]
            assert "similarity" in results[0]
            assert "metadata" in results[0]
    
    def test_search_theory_haskell(self, sample_haskell_query):
        """Test: Buscar teoría en tabla Haskell."""
        rag = get_rag_instance()
        
        results = rag.search_theory(
            query=sample_haskell_query,
            table_name="haskell",
            query_name="haskell_search",
            match_count=3
        )
        
        assert isinstance(results, list)
        if results:
            assert len(results) <= 3
    
    def test_search_theory_prolog(self, sample_prolog_query):
        """Test: Buscar teoría en tabla Prolog."""
        rag = get_rag_instance()
        
        results = rag.search_theory(
            query=sample_prolog_query,
            table_name="prolog",
            query_name="prolog_search",
            match_count=3
        )
        
        assert isinstance(results, list)
        if results:
            assert len(results) <= 3
    
    def test_format_results_empty(self):
        """Test: Formatear resultados vacíos."""
        rag = get_rag_instance()
        
        formatted = rag.format_results([])
        
        assert "No se encontró información relevante" in formatted
    
    def test_format_results_with_data(self):
        """Test: Formatear resultados con datos."""
        rag = get_rag_instance()
        
        mock_results = [
            {
                "content": "Un objeto en Wollok encapsula estado y comportamiento.",
                "similarity": 0.85,
                "metadata": {"source": "Guía de Wollok"}
            }
        ]
        
        formatted = rag.format_results(mock_results)
        
        assert "# Teoría Recuperada" in formatted
        assert "Fragmento 1" in formatted
        assert "0.850" in formatted
        assert "Guía de Wollok" in formatted
    
    def test_embedding_model_via_openrouter(self):
        """Test: Verificar que embeddings usan OpenRouter."""
        rag = get_rag_instance()
        
        # Verificar configuración del modelo de embeddings
        assert hasattr(rag.embeddings, 'model')
        assert "text-embedding-3-small" in rag.embeddings.model
        
        # Verificar que usa OpenRouter base_url
        if hasattr(rag.embeddings, 'openai_api_base'):
            assert "openrouter.ai" in rag.embeddings.openai_api_base


class TestRecuperarTeoriaTool:
    """Tests para la tool recuperar_teoria."""
    
    def test_recuperar_teoria_basic(self, sample_wollok_query):
        """Test: Usar recuperar_teoria sin config específica."""
        # recuperar_teoria es un StructuredTool, usar .invoke()
        result = recuperar_teoria.invoke({"query": sample_wollok_query})
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_recuperar_teoria_with_config(self, sample_haskell_query, agent_configs):
        """Test: Usar recuperar_teoria con config de agente."""
        haskell_config = agent_configs["Haskell"]
        
        # recuperar_teoria es un StructuredTool, usar .invoke()
        result = recuperar_teoria.invoke({
            "query": sample_haskell_query,
            "agent_config": haskell_config
        })
        
        assert isinstance(result, str)
        assert len(result) > 0

