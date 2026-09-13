"""
Tools del agente: RAG (LangChain) y extracción de PDFs/imágenes.
"""

import base64
import os
from functools import partial
from io import BytesIO
from typing import Any, Dict, Optional

import PyPDF2
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from PIL import Image

from app.infra.rag import get_rag_instance


@tool
def recuperar_teoria(query: str, agent_config: Dict[str, Any] = None) -> str:
    """
    Recupera teoría relevante desde la base de conocimientos usando búsqueda semántica.

    Args:
        query: La pregunta o concepto a buscar
        agent_config: Configuración del agente con tabla y query_name
    """
    try:
        rag = get_rag_instance()
        if agent_config is None:
            table_name = "wollok"
            query_name = "wollok_search"
        else:
            table_name = agent_config.get("table", "wollok")
            query_name = agent_config.get("query_name", "wollok_search")
        results = rag.search_theory(
            query=query,
            table_name=table_name,
            query_name=query_name,
            match_count=5,
        )
        return rag.format_results(results)
    except Exception as e:
        return f"Error al recuperar teoría: {str(e)}"


def create_recuperar_teoria_tool(agent_config: Dict[str, Any]):
    configured_tool = partial(recuperar_teoria, agent_config=agent_config)
    configured_tool.__name__ = "recuperar_teoria"
    configured_tool.__doc__ = recuperar_teoria.__doc__
    return tool(configured_tool)


class FileExtractor:
    def __init__(self):
        openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
        if openrouter_api_key:
            self.vision_model = ChatOpenAI(
                model="openai/gpt-4o-mini",
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_api_key,
                temperature=0.3,
            )
        else:
            self.vision_model = None

    def extract_from_pdf(self, pdf_file) -> str:
        try:
            pdf_file.seek(0)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += f"\n--- Página {page_num + 1} ---\n"
                text += page.extract_text()
            if not text.strip():
                return "⚠️ El PDF no contiene texto extraíble (puede ser una imagen escaneada)."
            return text.strip()
        except Exception as e:
            return f"❌ Error al extraer texto del PDF: {str(e)}"

    def extract_from_image(self, image_file) -> str:
        try:
            if self.vision_model is None:
                return "⚠️ Análisis de imágenes no disponible. Configure OPENROUTER_API_KEY."
            image_file.seek(0)
            image = Image.open(image_file)
            if image.mode != "RGB":
                image = image.convert("RGB")
            buffered = BytesIO()
            image.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            prompt = """Analiza esta imagen y extrae toda la información relevante:
            - Si contiene código, transcríbelo exactamente
            - Si contiene texto, extráelo completamente
            - Si es un diagrama o gráfico, descríbelo en detalle
            - Si contiene ejercicios o problemas, transcríbelos fielmente

            Responde en español de manera clara y estructurada."""
            from langchain_core.messages import HumanMessage

            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_base64}",
                            "detail": "high",
                        },
                    },
                ]
            )
            response = self.vision_model.invoke([message])
            return response.content
        except Exception as e:
            import traceback

            print(f"Error detallado al analizar imagen: {traceback.format_exc()}")
            return f"❌ Error al analizar la imagen: {str(e)}"

    def extract_from_file(self, uploaded_file) -> Optional[str]:
        if uploaded_file is None:
            return None
        file_name = uploaded_file.name.lower()
        if file_name.endswith(".pdf"):
            return self.extract_from_pdf(uploaded_file)
        if file_name.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")):
            return self.extract_from_image(uploaded_file)
        return f"⚠️ Tipo de archivo no soportado: {file_name}"


_extractor_instance = None


def get_file_extractor() -> FileExtractor:
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = FileExtractor()
    return _extractor_instance
