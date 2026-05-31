"""
Módulo de herramientas para ChatPdeP.
Incluye RAG, extracción de archivos y otras utilidades.
"""

from .rag_tool import get_rag_instance, recuperar_teoria, SupabaseRAG

try:
    from .file_extraction import get_file_extractor, FileExtractor
    _file_extraction_available = True
except ImportError:
    _file_extraction_available = False

__all__ = [
    "get_rag_instance",
    "recuperar_teoria",
    "SupabaseRAG",
    "get_file_extractor",
    "FileExtractor",
]

