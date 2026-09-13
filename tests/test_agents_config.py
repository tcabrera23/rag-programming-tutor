"""
Tests para la configuración de agentes (app/domain/agents.py).
"""

import pytest
from app.domain.agents import AGENTS, get_agent_config, AGENT_WOLLOK, AGENT_HASKELL, AGENT_PROLOG


class TestAgentsConfig:
    """Tests para configuración de agentes."""
    
    def test_agents_dictionary_exists(self):
        """Test: Verificar que existe el diccionario AGENTS."""
        assert AGENTS is not None
        assert isinstance(AGENTS, dict)
        assert len(AGENTS) == 3
    
    def test_all_agents_present(self):
        """Test: Verificar que todos los agentes estén presentes."""
        assert "Wollok" in AGENTS
        assert "Haskell" in AGENTS
        assert "Prolog" in AGENTS
    
    def test_wollok_config(self):
        """Test: Verificar configuración de Wollok."""
        config = AGENT_WOLLOK
        
        assert config["name"] == "Wollok"
        assert config["table"] == "wollok"
        assert config["query_name"] == "wollok_search"
        assert "system_prompt" in config
        assert len(config["system_prompt"]) > 100
    
    def test_haskell_config(self):
        """Test: Verificar configuración de Haskell."""
        config = AGENT_HASKELL
        
        assert config["name"] == "Haskell"
        assert config["table"] == "haskell"
        assert config["query_name"] == "haskell_search"
        assert "system_prompt" in config
    
    def test_prolog_config(self):
        """Test: Verificar configuración de Prolog."""
        config = AGENT_PROLOG
        
        assert config["name"] == "Prolog"
        assert config["table"] == "prolog"
        assert config["query_name"] == "prolog_search"
        assert "system_prompt" in config
    
    def test_get_agent_config(self):
        """Test: Obtener config de agente por nombre."""
        wollok_config = get_agent_config("Wollok")
        haskell_config = get_agent_config("Haskell")
        prolog_config = get_agent_config("Prolog")
        
        assert wollok_config["name"] == "Wollok"
        assert haskell_config["name"] == "Haskell"
        assert prolog_config["name"] == "Prolog"
    
    def test_get_agent_config_invalid(self):
        """Test: Obtener config con nombre inválido retorna Wollok por defecto."""
        config = get_agent_config("InvalidAgent")
        
        # Debería retornar Wollok por defecto
        assert config["name"] == "Wollok"
    
    def test_system_prompts_content(self):
        """Test: Verificar que los system prompts tengan contenido clave."""
        for agent_name, agent_config in AGENTS.items():
            prompt = agent_config["system_prompt"]
            
            # Verificar que contengan instrucciones clave
            assert "recuperar_teoria" in prompt.lower()
            assert "tool" in prompt.lower()
            assert "código" in prompt.lower() or "codigo" in prompt.lower()

