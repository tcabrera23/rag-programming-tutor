"""
Gestor de modelos LLM con soporte para cloud (OpenRouter) y local (Ollama).
Incluye sistema de fallbacks y clasificación automática de modelos.
"""

import os
from typing import Optional, Dict, List, Literal
from dataclasses import dataclass

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False


def _in_streamlit() -> bool:
    """True solo cuando estamos dentro de un script corriendo con `streamlit run`."""
    if not STREAMLIT_AVAILABLE:
        return False
    # Evitar acceder a session_state fuera de un contexto Streamlit real
    # comprobando la variable de entorno que Streamlit setea en su server.
    import os
    return bool(os.getenv("STREAMLIT_SERVER_PORT") or os.getenv("STREAMLIT_SHARING_MODE"))

# LangChain imports
try:
    from langchain_openai import ChatOpenAI
    from langchain_community.chat_models import ChatOllama
    from langchain_groq import ChatGroq
except ImportError:
    # Fallback para testing
    ChatOpenAI = None
    ChatOllama = None
    ChatGroq = None


ModelProvider = Literal["openrouter", "ollama", "groq"]
ModelTier = Literal["economy", "balanced", "premium"]


@dataclass
class ModelConfig:
    """Configuración de un modelo LLM."""
    id: str
    name: str
    provider: ModelProvider
    tier: ModelTier
    input_cost: str  # Costo por 1M tokens
    output_cost: str
    description: str
    context_window: int
    is_custom: bool = False


class ModelManager:
    """
    Gestor centralizado de modelos LLM.
    
    Características:
    - Soporte para OpenRouter y Ollama
    - Modelos predefinidos y personalizados
    - Sistema de fallbacks
    - Clasificación por tier (economy/balanced/premium)
    """
    
    # Modelos predefinidos por tier
    PREDEFINED_MODELS = {
        # ECONOMY TIER - Bajo costo
        "google/gemini-2.5-flash-lite": ModelConfig(
            id="google/gemini-2.5-flash-lite",
            name="Gemini 2.5 Flash Lite",
            provider="openrouter",
            tier="economy",
            input_cost="$0.10",
            output_cost="$0.40",
            description="Rápido y económico - Ideal para consultas teóricas",
            context_window=1_000_000
        ),
        
        # BALANCED TIER - Costo-beneficio
        "openai/gpt-5.1-codex-mini": ModelConfig(
            id="openai/gpt-5.1-codex-mini",
            name="GPT 5 Codex Mini",
            provider="openrouter",
            tier="balanced",
            input_cost="$0.25",
            output_cost="$2.00",
            description="Potente y económico para código",
            context_window=128_000
        ),
        "x-ai/grok-4.1-fast": ModelConfig(
            id="x-ai/grok-4.1-fast",
            name="Grok 4.1 Fast",
            provider="openrouter",
            tier="balanced",
            input_cost="$0.20",
            output_cost="$0.50",
            description="Potente y rápido - Excelente para código",
            context_window=128_000
        ),
        "qwen/qwen3-coder": ModelConfig(
            id="qwen/qwen3-coder",
            name="Qwen 3 Coder",
            provider="openrouter",
            tier="balanced",
            input_cost="$0.22",
            output_cost="$0.95",
            description="Especializado en código - Muy eficiente",
            context_window=32_000
        ),
        
        # PREMIUM TIER - Máxima calidad
        "anthropic/claude-opus-4.6": ModelConfig(
            id="anthropic/claude-opus-4.6",
            name="Claude Opus 4.6",
            provider="openrouter",
            tier="premium",
            input_cost="$5.00",
            output_cost="$25.00",
            description="El Rey del código - Máxima calidad",
            context_window=200_000
        ),
    }
    
    # Modelos de Groq (API Gratuita)
    # groq/compound: sistema agentico con búsqueda web y ejecución de código
    # https://console.groq.com/docs/models
    GROQ_MODELS = [
        ModelConfig(
            id="groq/compound",
            name="Groq Compound",
            provider="groq",
            tier="balanced",
            input_cost="$0 (Gratis)",
            output_cost="$0 (Gratis)",
            description="Sistema agentico con herramientas integradas (web search, code execution)",
            context_window=131_072,
        ),
    ]
    
    # Modelos locales sugeridos (Ollama)
    SUGGESTED_LOCAL_MODELS = [
        ModelConfig(
            id="phi4-mini",
            name="Phi 4 Mini (3.8B)",
            provider="ollama",
            tier="economy",
            input_cost="$0 (Local)",
            output_cost="$0 (Local)",
            description="Preguntas simples y teoría - Incluido por defecto",
            context_window=128_000,
        ),
        ModelConfig(
            id="qwen3:4b",
            name="Qwen 3 4B",
            provider="ollama",
            tier="balanced",
            input_cost="$0 (Local)",
            output_cost="$0 (Local)",
            description="Código y consultas complejas - Incluido por defecto",
            context_window=32_768,
        ),
        ModelConfig(
            id="deepseek-coder:6.7b",
            name="DeepSeek Coder 6.7B",
            provider="ollama",
            tier="balanced",
            input_cost="$0 (Local)",
            output_cost="$0 (Local)",
            description="Especialista en código - Recomendado",
            context_window=16_000,
        ),
        ModelConfig(
            id="qwen2.5-coder:7b",
            name="Qwen 2.5 Coder 7B",
            provider="ollama",
            tier="balanced",
            input_cost="$0 (Local)",
            output_cost="$0 (Local)",
            description="Coder potente - Muy recomendado",
            context_window=32_000,
        ),
    ]
    
    def __init__(self):
        """Inicializa el gestor de modelos."""
        self.custom_models: Dict[str, ModelConfig] = {}
        self._load_custom_models_from_session()
    
    def _load_custom_models_from_session(self):
        """Carga modelos personalizados desde st.session_state (solo en Streamlit)."""
        if _in_streamlit() and "custom_models" in st.session_state:
            self.custom_models = st.session_state.custom_models

    def _save_custom_models_to_session(self):
        """Guarda modelos personalizados en st.session_state (solo en Streamlit)."""
        if _in_streamlit():
            st.session_state.custom_models = self.custom_models
    
    def add_custom_model(
        self,
        model_id: str,
        provider: ModelProvider,
        name: Optional[str] = None,
        tier: ModelTier = "balanced"
    ) -> ModelConfig:
        """
        Agrega un modelo personalizado.
        
        Args:
            model_id: ID del modelo (ej: "openai/gpt-4" o "llama3")
            provider: "openrouter" o "ollama"
            name: Nombre descriptivo (opcional)
            tier: Tier del modelo
        
        Returns:
            ModelConfig creado
        """
        if name is None:
            name = model_id.split("/")[-1].title()
        
        config = ModelConfig(
            id=model_id,
            name=name,
            provider=provider,
            tier=tier,
            input_cost="Custom",
            output_cost="Custom",
            description="Modelo personalizado",
            context_window=32_000,  # Default conservador
            is_custom=True
        )
        
        self.custom_models[model_id] = config
        self._save_custom_models_to_session()
        
        return config
    
    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Obtiene configuración de un modelo por su ID."""
        # Buscar en predefinidos
        if model_id in self.PREDEFINED_MODELS:
            return self.PREDEFINED_MODELS[model_id]
        
        # Buscar en personalizados
        if model_id in self.custom_models:
            return self.custom_models[model_id]
        
        # Buscar en sugeridos locales
        for model in self.SUGGESTED_LOCAL_MODELS:
            if model.id == model_id:
                return model
        
        # Buscar en Groq
        for model in self.GROQ_MODELS:
            if model.id == model_id:
                return model
        
        return None
    
    def get_models_by_provider(self, provider: ModelProvider) -> List[ModelConfig]:
        """Obtiene todos los modelos de un proveedor específico."""
        models = []
        
        # Predefinidos
        for model in self.PREDEFINED_MODELS.values():
            if model.provider == provider:
                models.append(model)
        
        # Personalizados
        for model in self.custom_models.values():
            if model.provider == provider:
                models.append(model)
        
        # Sugeridos locales (solo si es ollama)
        if provider == "ollama":
            models.extend(self.SUGGESTED_LOCAL_MODELS)
        
        # Modelos Groq (solo si es groq)
        if provider == "groq":
            models.extend(self.GROQ_MODELS)
        
        return models
    
    def get_models_by_tier(self, tier: ModelTier) -> List[ModelConfig]:
        """Obtiene todos los modelos de un tier específico."""
        models = []
        
        for model in self.PREDEFINED_MODELS.values():
            if model.tier == tier:
                models.append(model)
        
        for model in self.custom_models.values():
            if model.tier == tier:
                models.append(model)
        
        return models
    
    def get_all_models(self) -> List[ModelConfig]:
        """Obtiene todos los modelos disponibles."""
        models = list(self.PREDEFINED_MODELS.values())
        models.extend(self.custom_models.values())
        return models
    
    def get_fallback_model(self) -> ModelConfig:
        """
        Obtiene el modelo de fallback por defecto (Groq Llama 3.3 Versatile).
        """
        # Usamos Llama 3.3 Versatile de Groq como fallback por ser gratuito y robusto
        return self.GROQ_MODELS[0]
    
    def create_llm(
        self,
        model_id: str,
        temperature: float = 0.5,
        **kwargs
    ):
        """
        Crea una instancia de LLM según el modelo seleccionado.
        
        Args:
            model_id: ID del modelo
            temperature: Temperatura del modelo
            **kwargs: Parámetros adicionales
        
        Returns:
            Instancia de ChatOpenAI o ChatOllama
        
        Raises:
            ValueError: Si el modelo no existe o falta configuración
        """
        model_config = self.get_model(model_id)
        
        if model_config is None:
            raise ValueError(f"Modelo {model_id} no encontrado")
        
        # Crear LLM según proveedor
        if model_config.provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY no configurada")
            
            return ChatOpenAI(
                model=model_id,
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                temperature=temperature,
                **kwargs
            )
        
        elif model_config.provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            
            return ChatOllama(
                model=model_id,
                base_url=base_url,
                temperature=temperature,
                **kwargs
            )
        
        elif model_config.provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY no configurada")
            
            return ChatGroq(
                model=model_id,
                groq_api_key=api_key,
                temperature=temperature,
                **kwargs
            )
        
        else:
            raise ValueError(f"Proveedor {model_config.provider} no soportado")
    
    def create_llm_with_fallback(
        self,
        model_id: str,
        temperature: float = 0.5,
        **kwargs
    ):
        """
        Crea LLM con fallback automático a Gemini si falla.
        
        Args:
            model_id: ID del modelo principal
            temperature: Temperatura
            **kwargs: Parámetros adicionales
        
        Returns:
            Tupla (llm, is_fallback: bool, fallback_reason: Optional[str])
        """
        try:
            llm = self.create_llm(model_id, temperature, **kwargs)
            return llm, False, None
        
        except Exception as e:
            # Usar fallback
            fallback_config = self.get_fallback_model()
            fallback_reason = str(e)
            
            try:
                llm = self.create_llm(fallback_config.id, temperature, **kwargs)
                return llm, True, fallback_reason
            except Exception as fallback_error:
                raise ValueError(
                    f"Modelo principal falló: {fallback_reason}. "
                    f"Fallback también falló: {str(fallback_error)}"
                )
    
    def suggest_model_by_tier(self, tier: ModelTier, provider: Optional[ModelProvider] = None) -> ModelConfig:
        """
        Sugiere un modelo según tier y opcionalmente proveedor.
        
        Args:
            tier: Tier deseado
            provider: Proveedor opcional (openrouter/ollama)
        
        Returns:
            ModelConfig sugerido
        """
        models = self.get_models_by_tier(tier)
        
        if provider:
            models = [m for m in models if m.provider == provider]
        
        if not models:
            # Fallback a Gemini si no hay modelos del tier
            return self.get_fallback_model()
        
        # Retornar primer modelo del tier
        return models[0]


# Singleton global
_manager_instance = None

def get_model_manager() -> ModelManager:
    """Obtiene instancia singleton del gestor de modelos."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ModelManager()
    return _manager_instance
