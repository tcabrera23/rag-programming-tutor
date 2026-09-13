"""
Interfaz Streamlit para ChatPdeP.
Presentación y persistencia de UI; el turno de chat vive en app.services.chat.
"""

import os
import time
import uuid
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from app.domain.agents import AGENTS
from app.domain.tools import get_file_extractor
from app.infra.database import SQLiteDatabase
from app.infra.llm import get_model_manager
from app.services.chat import TurnResult, get_chat_service

load_dotenv()


def _e2e_enabled() -> bool:
    return os.getenv("CHATPDP_E2E") == "1"


def is_streamlit_cloud() -> bool:
    if os.getenv("STREAMLIT_SHARING_MODE") or os.getenv("STREAMLIT_CLOUD"):
        return True
    try:
        test_file = "data/.write_test"
        os.makedirs("data", exist_ok=True)
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return False
    except (OSError, IOError, PermissionError):
        return True


class SessionStateDatabase:
    def __init__(self):
        if "conversations_data" not in st.session_state:
            st.session_state.conversations_data = {}
        if "messages_data" not in st.session_state:
            st.session_state.messages_data = {}

    def create_conversation(self, conversation_id, title, agent_name, model_name) -> bool:
        if conversation_id in st.session_state.conversations_data:
            return False
        st.session_state.conversations_data[conversation_id] = {
            "conversation_id": conversation_id,
            "title": title,
            "agent_name": agent_name,
            "model_name": model_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        st.session_state.messages_data[conversation_id] = []
        return True

    def add_message(
        self,
        conversation_id,
        role,
        content,
        has_attachment=False,
        attachment_type=None,
    ) -> bool:
        if conversation_id not in st.session_state.messages_data:
            st.session_state.messages_data[conversation_id] = []
        message = {
            "role": role,
            "content": content,
            "created_at": datetime.now().isoformat(),
        }
        if has_attachment:
            message["attachment_type"] = attachment_type
        st.session_state.messages_data[conversation_id].append(message)
        if conversation_id in st.session_state.conversations_data:
            st.session_state.conversations_data[conversation_id]["updated_at"] = (
                datetime.now().isoformat()
            )
        return True

    def get_conversation_messages(self, conversation_id):
        return st.session_state.messages_data.get(conversation_id, [])

    def get_all_conversations(self):
        conversations = list(st.session_state.conversations_data.values())
        conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        return conversations

    def update_conversation_title(self, conversation_id, new_title) -> bool:
        if conversation_id in st.session_state.conversations_data:
            st.session_state.conversations_data[conversation_id]["title"] = new_title
            st.session_state.conversations_data[conversation_id]["updated_at"] = (
                datetime.now().isoformat()
            )
            return True
        return False

    def delete_conversation(self, conversation_id) -> bool:
        st.session_state.conversations_data.pop(conversation_id, None)
        st.session_state.messages_data.pop(conversation_id, None)
        return True

    def get_conversation_info(self, conversation_id):
        return st.session_state.conversations_data.get(conversation_id)


def get_ui_database():
    if is_streamlit_cloud():
        return SessionStateDatabase()
    db_path = os.getenv("CHATPDP_DB_PATH", "data/conversations.db")
    return SQLiteDatabase(db_path=db_path)


st.set_page_config(
    page_title="ChatPdeP - Tutor de Paradigmas",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .sidebar .element-container {
        margin-bottom: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

if "db" not in st.session_state:
    st.session_state.db = get_ui_database()

if "file_extractor" not in st.session_state:
    st.session_state.file_extractor = get_file_extractor()

if "model_manager" not in st.session_state:
    st.session_state.model_manager = get_model_manager()

if "custom_models" not in st.session_state:
    st.session_state.custom_models = {}
else:
    st.session_state.model_manager.custom_models = st.session_state.custom_models

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = f"conv_{uuid.uuid4().hex[:8]}_{int(time.time())}"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_agent" not in st.session_state:
    st.session_state.current_agent = "Wollok"

if "model_provider" not in st.session_state:
    st.session_state.model_provider = (
        "openrouter"
        if os.getenv("OPENROUTER_API_KEY") and not os.getenv("GROQ_API_KEY")
        else "groq"
    )

if "current_model" not in st.session_state:
    st.session_state.current_model = (
        "google/gemini-2.5-flash-lite"
        if st.session_state.model_provider == "openrouter"
        else "groq/compound"
    )

if "auto_classify" not in st.session_state:
    st.session_state.auto_classify = True

if "is_new_conversation" not in st.session_state:
    st.session_state.is_new_conversation = True

with st.sidebar:
    st.markdown("## ⚙️ Configuración")
    st.markdown("### 🌐 Proveedor de Modelo")

    provider_options = ["groq", "openrouter", "ollama"]
    provider_labels = {
        "groq": "⚡ Groq (Gratis)",
        "openrouter": "☁️ OpenRouter (Pago)",
        "ollama": "💻 Local (Ollama)",
    }

    current_index = (
        provider_options.index(st.session_state.model_provider)
        if st.session_state.model_provider in provider_options
        else 0
    )

    provider = st.radio(
        "Selecciona el proveedor",
        options=provider_options,
        format_func=lambda x: provider_labels[x],
        index=current_index,
        key="selector_proveedor",
        help="Groq: API gratuita ideal para empezar | OpenRouter: Acceso a todos los modelos | Ollama: Modelos locales sin costo",
    )
    st.session_state.model_provider = provider

    if provider == "groq":
        groq_key = st.text_input(
            "Groq API Key (Gratis)",
            value="",
            type="password",
            help="Obtén tu API key gratis en https://console.groq.com/keys",
        )
        if groq_key:
            os.environ["GROQ_API_KEY"] = groq_key
        st.info("💡 **¡Groq es gratis!** Obtén tu API key en [console.groq.com](https://console.groq.com)")
    elif provider == "openrouter":
        openrouter_key = st.text_input(
            "OpenRouter API Key",
            value="",
            type="password",
            help="Tu API key de OpenRouter para usar los modelos",
        )
        if openrouter_key:
            os.environ["OPENROUTER_API_KEY"] = openrouter_key
    else:
        ollama_url = st.text_input(
            "Ollama Base URL",
            value=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            help="URL del servidor Ollama (ej: http://localhost:11434)",
        )
        os.environ["OLLAMA_BASE_URL"] = ollama_url
        with st.expander("📦 Modelos sugeridos para Ollama"):
            st.markdown(
                """
            Instala estos modelos con Docker o manualmente:

            **Por defecto en Docker:**
            ```bash
            phi4-mini (3.8B) - Rápido y ligero
            ```

            **Recomendados (vía comando):**
            ```bash
            ollama pull qwen3-4b
            ollama pull deepseek-coder-6.7b
            ollama pull qwen2.5-coder-7b
            ```
            """
            )

    st.markdown("---")
    st.markdown("### 🎓 Tutor")
    selected_agent = st.selectbox(
        "Selecciona el paradigma",
        options=list(AGENTS.keys()),
        index=list(AGENTS.keys()).index(st.session_state.current_agent),
        key="selector_tutor",
        help="Elige el lenguaje de programación sobre el que necesitas ayuda",
    )

    st.markdown("### 🤖 Modelo LLM")
    auto_classify = st.checkbox(
        "🎯 Auto-clasificar (optimizar costos)",
        value=st.session_state.auto_classify,
        key="check_auto_clasificar",
        help="Clasifica automáticamente la consulta y selecciona el modelo más apropiado según dificultad",
    )
    st.session_state.auto_classify = auto_classify

    model_manager = st.session_state.model_manager
    available_models = model_manager.get_models_by_provider(provider)
    model_options = {model.id: model for model in available_models}

    if not model_options:
        st.warning(f"⚠️ No hay modelos disponibles para {provider}")
        st.stop()

    selected_model_id = st.selectbox(
        "Modelo manual (si auto-clasificar desactivado)",
        options=list(model_options.keys()),
        index=(
            list(model_options.keys()).index(st.session_state.current_model)
            if st.session_state.current_model in model_options
            else 0
        ),
        help="Modelo de lenguaje a utilizar",
        format_func=lambda x: model_options[x].name,
        disabled=auto_classify,
    )

    selected_model_config = model_options[selected_model_id]
    st.caption(
        f"**💰 Costo:** Input: {selected_model_config.input_cost} | Output: {selected_model_config.output_cost}"
    )
    st.caption(f"_{selected_model_config.description}_")
    st.caption(f"**🔧 Tier:** {selected_model_config.tier.upper()}")

    with st.expander("➕ Agregar modelo personalizado"):
        st.markdown("Agrega un modelo desde OpenRouter o Ollama:")
        custom_provider = st.radio(
            "Proveedor del modelo personalizado",
            options=["groq", "openrouter", "ollama"],
            format_func=lambda x: "Groq" if x == "groq" else ("OpenRouter" if x == "openrouter" else "Ollama"),
            key="custom_provider",
        )
        placeholder_map = {
            "groq": "groq/compound",
            "openrouter": "openai/gpt-4o",
            "ollama": "llama3",
        }
        custom_model_id = st.text_input(
            "ID del modelo",
            placeholder=placeholder_map.get(custom_provider, "model-id"),
            help="Copia el ID desde la documentación del proveedor",
            key="custom_model_id",
        )
        custom_model_name = st.text_input(
            "Nombre descriptivo (opcional)",
            placeholder="GPT-4o",
            key="custom_model_name",
        )
        custom_tier = st.selectbox(
            "Tier",
            options=["economy", "balanced", "premium"],
            index=1,
            key="custom_tier",
        )
        if st.button("➕ Agregar Modelo", key="add_custom_model"):
            if custom_model_id:
                try:
                    model_manager.add_custom_model(
                        model_id=custom_model_id,
                        provider=custom_provider,
                        name=custom_model_name if custom_model_name else None,
                        tier=custom_tier,
                    )
                    st.session_state.custom_models = model_manager.custom_models
                    st.success(f"✅ Modelo {custom_model_id} agregado exitosamente!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al agregar modelo: {str(e)}")
            else:
                st.warning("⚠️ Por favor ingresa el ID del modelo")

    context_window = st.slider(
        "Ventana de contexto (mensajes)",
        min_value=4,
        max_value=20,
        value=8,
        step=2,
        help="Número de mensajes previos a mantener en memoria",
    )

    def _start_new_conversation():
        st.session_state.conversation_id = f"conv_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        st.session_state.messages = []
        st.session_state.is_new_conversation = True

    def _load_conversation(conv_id: str):
        loaded = st.session_state.db.get_conversation_messages(conv_id)
        info = st.session_state.db.get_conversation_info(conv_id)
        st.session_state.conversation_id = conv_id
        st.session_state.messages = loaded
        st.session_state.is_new_conversation = False
        if info:
            st.session_state.current_agent = info["agent_name"]
            st.session_state.selector_tutor = info["agent_name"]
            st.session_state.current_model = info["model_name"]

    def _delete_conversation(conv_id: str):
        st.session_state.db.delete_conversation(conv_id)
        if st.session_state.conversation_id == conv_id:
            _start_new_conversation()

    st.markdown("---")
    st.button(
        "➕ Nueva Conversación",
        use_container_width=True,
        key="nueva_conversacion",
        on_click=_start_new_conversation,
    )

    st.markdown("### 📚 Historial")
    conversations = st.session_state.db.get_all_conversations()
    if conversations:
        for conv in conversations[:10]:
            col1, col2 = st.columns([4, 1])
            is_current = conv["conversation_id"] == st.session_state.conversation_id
            with col1:
                button_label = f"{'✅' if is_current else '💬'} {conv['title'][:30]}..."
                st.button(
                    button_label,
                    key=f"load_{conv['conversation_id']}",
                    use_container_width=True,
                    type="primary" if is_current else "secondary",
                    on_click=_load_conversation,
                    args=(conv["conversation_id"],),
                )
            with col2:
                st.button(
                    "🗑️",
                    key=f"del_{conv['conversation_id']}",
                    on_click=_delete_conversation,
                    args=(conv["conversation_id"],),
                )
    else:
        st.info("No hay conversaciones previas")

st.markdown('<div class="main-header">🎓 ChatPdeP</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Tu tutor de Paradigmas de Programación - UTN FRBA</div>',
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)
with col1:
    st.info(f"**Tutor:** {selected_agent}")
with col2:
    if st.session_state.auto_classify:
        st.info("**Modelo:** 🎯 Auto (optimizando)")
    else:
        st.info(f"**Modelo:** {selected_model_id.split('/')[-1]}")
with col3:
    st.info(f"**Contexto:** {context_window} msgs")

st.session_state.current_agent = selected_agent
st.session_state.current_model = selected_model_id

st.markdown("---")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("attachment_type"):
            st.caption(f"📎 Archivo adjunto: {message['attachment_type']}")

uploaded_file = st.file_uploader(
    "📎 Adjuntar archivo (opcional)",
    type=["pdf", "png", "jpg", "jpeg"],
    help="Puedes adjuntar un PDF o imagen con tu pregunta",
)

if prompt := st.chat_input("Escribe tu pregunta sobre " + selected_agent + "..."):
    if not _e2e_enabled() and not os.getenv("OPENROUTER_API_KEY"):
        st.error("⚠️ Por favor, configura tu OpenRouter API Key en el sidebar")
        st.stop()

    extracted_content = None
    attachment_type = None
    if uploaded_file is not None:
        with st.spinner("📄 Procesando archivo adjunto..."):
            extracted_content = st.session_state.file_extractor.extract_from_file(uploaded_file)
            attachment_type = "pdf" if uploaded_file.name.endswith(".pdf") else "image"

    full_message = prompt
    if extracted_content:
        full_message += f"\n\n--- Contenido del archivo adjunto ---\n{extracted_content}"

    st.session_state.messages.append(
        {"role": "user", "content": prompt, "attachment_type": attachment_type}
    )

    with st.chat_message("user"):
        st.markdown(prompt)
        if attachment_type:
            st.caption(f"📎 Archivo adjunto: {attachment_type}")

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            with st.spinner("🤔 Pensando..."):
                history = st.session_state.messages[:-1]
                if _e2e_enabled():
                    result = TurnResult(
                        content=f"E2E: {prompt}",
                        model_id=selected_model_id,
                    )
                else:
                    result = get_chat_service().run_turn(
                        agent_name=selected_agent,
                        messages_history=history,
                        user_message=prompt,
                        model_id=selected_model_id,
                        context_window=context_window,
                        auto_classify=st.session_state.auto_classify,
                        attachment_content=extracted_content,
                        attachment_type=attachment_type,
                        provider=provider,
                    )

                if result.classification:
                    suggested = model_manager.get_model(result.model_id)
                    st.info(f"🎯 **Clasificación:** {result.classification.reasoning}")
                    if suggested:
                        st.info(f"🤖 **Modelo seleccionado:** {suggested.name}")

                if result.is_fallback:
                    fallback_config = model_manager.get_fallback_model()
                    if provider == "ollama":
                        st.error(f"⚠️ **Error en modelo local:** {result.fallback_reason}")
                        st.warning(
                            "🔄 Por favor selecciona un modelo cloud desde el sidebar o verifica que Ollama esté corriendo."
                        )
                        st.info(f"💡 Usando fallback: {fallback_config.name}")
                    else:
                        st.warning(
                            f"⚠️ Modelo seleccionado falló. Usando fallback: {fallback_config.name}"
                        )
                        st.caption(f"Razón: {result.fallback_reason}")

                if result.summarized:
                    st.info(
                        f"💡 Conversación resumida ({result.tokens_before} → {result.tokens_after} tokens aprox.)"
                    )

                assistant_message = result.content
                message_placeholder.markdown(assistant_message)
                st.session_state.messages.append(
                    {"role": "assistant", "content": assistant_message}
                )

                if st.session_state.is_new_conversation:
                    title = prompt[:50] if len(prompt) <= 50 else prompt[:47] + "..."
                    st.session_state.db.create_conversation(
                        conversation_id=st.session_state.conversation_id,
                        title=title,
                        agent_name=selected_agent,
                        model_name=result.model_id,
                    )
                    st.session_state.is_new_conversation = False

                st.session_state.db.add_message(
                    conversation_id=st.session_state.conversation_id,
                    role="user",
                    content=full_message,
                    has_attachment=attachment_type is not None,
                    attachment_type=attachment_type,
                )
                st.session_state.db.add_message(
                    conversation_id=st.session_state.conversation_id,
                    role="assistant",
                    content=assistant_message,
                )
                st.rerun()
        except Exception as e:
            error_message = f"❌ Error al generar respuesta: {str(e)}"
            message_placeholder.error(error_message)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_message}
            )
