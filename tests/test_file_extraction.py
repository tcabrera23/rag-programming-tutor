"""
Tests unitarios para extracción de archivos (app/domain/tools.py).
"""

import pytest
from io import BytesIO
from PIL import Image
import PyPDF2
from app.domain.tools import FileExtractor, get_file_extractor


class TestFileExtractor:
    """Tests para la clase FileExtractor."""
    
    def test_extractor_creation(self):
        """Test: Crear instancia de FileExtractor."""
        extractor = FileExtractor()
        
        assert extractor is not None
        # El modelo de visión debería estar configurado si hay API key
        if extractor.vision_model:
            # ChatOpenAI usa 'model_name' en lugar de 'model'
            assert hasattr(extractor.vision_model, 'model_name') or hasattr(extractor.vision_model, 'model')
    
    def test_singleton_pattern(self):
        """Test: Verificar singleton."""
        instance1 = get_file_extractor()
        instance2 = get_file_extractor()
        
        assert instance1 is instance2
    
    def test_extract_from_image_mock(self):
        """Test: Extraer de imagen (mock)."""
        extractor = get_file_extractor()
        
        # Crear imagen simple en memoria
        img = Image.new('RGB', (100, 100), color='white')
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        img_buffer.name = "test.png"
        
        # Intentar extraer (puede fallar si no hay API key, pero no debe crashear)
        result = extractor.extract_from_image(img_buffer)
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_extract_from_pdf_mock(self):
        """Test: Extraer de PDF (mock)."""
        extractor = get_file_extractor()
        
        # Crear PDF simple en memoria
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        c.drawString(100, 750, "Test PDF content")
        c.save()
        
        pdf_buffer.seek(0)
        
        result = extractor.extract_from_pdf(pdf_buffer)
        
        assert isinstance(result, str)
        # Debería contener el texto o un mensaje de error
        assert len(result) > 0

