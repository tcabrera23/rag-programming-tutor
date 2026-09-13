"""
Tests unitarios para la base de datos SQLite (app/infra/database.py).
"""

import pytest
import os
import tempfile
from app.infra.database import SQLiteDatabase


class TestSQLiteDatabase:
    """Tests para la clase SQLiteDatabase."""
    
    @pytest.fixture
    def temp_db(self):
        """Crear base de datos temporal para tests."""
        # Crear archivo temporal
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Crear DB con el path temporal
        db = SQLiteDatabase(db_path=path)
        
        yield db
        
        # Cleanup - cerrar conexión antes de eliminar (Windows)
        if hasattr(db, 'conn'):
            db.conn.close()
        
        # Intentar eliminar el archivo con retry para Windows
        import time
        for _ in range(3):
            try:
                if os.path.exists(path):
                    os.unlink(path)
                break
            except PermissionError:
                time.sleep(0.1)
    
    def test_db_creation(self, temp_db):
        """Test: Crear base de datos."""
        assert temp_db is not None
        assert os.path.exists(temp_db.db_path)
    
    def test_create_conversation(self, temp_db):
        """Test: Crear nueva conversación."""
        success = temp_db.create_conversation(
            conversation_id="test_conv_001",
            title="Test Conversation",
            agent_name="Wollok",
            model_name="google/gemini-2.5-flash-lite"
        )
        
        assert success is True
    
    def test_create_duplicate_conversation(self, temp_db):
        """Test: Intentar crear conversación duplicada."""
        conv_id = "test_conv_002"
        
        # Primera creación
        success1 = temp_db.create_conversation(
            conversation_id=conv_id,
            title="Test",
            agent_name="Wollok",
            model_name="test-model"
        )
        
        # Segunda creación (duplicada)
        success2 = temp_db.create_conversation(
            conversation_id=conv_id,
            title="Test 2",
            agent_name="Haskell",
            model_name="test-model"
        )
        
        assert success1 is True
        assert success2 is False
    
    def test_add_message(self, temp_db):
        """Test: Agregar mensaje a conversación."""
        conv_id = "test_conv_003"
        
        # Crear conversación
        temp_db.create_conversation(
            conversation_id=conv_id,
            title="Test",
            agent_name="Wollok",
            model_name="test-model"
        )
        
        # Agregar mensaje
        success = temp_db.add_message(
            conversation_id=conv_id,
            role="user",
            content="¿Qué es un objeto?"
        )
        
        assert success is True
    
    def test_get_conversation_messages(self, temp_db):
        """Test: Obtener mensajes de conversación."""
        conv_id = "test_conv_004"
        
        # Crear conversación y agregar mensajes
        temp_db.create_conversation(
            conversation_id=conv_id,
            title="Test",
            agent_name="Wollok",
            model_name="test-model"
        )
        
        temp_db.add_message(conv_id, "user", "Pregunta 1")
        temp_db.add_message(conv_id, "assistant", "Respuesta 1")
        temp_db.add_message(conv_id, "user", "Pregunta 2")
        
        # Obtener mensajes
        messages = temp_db.get_conversation_messages(conv_id)
        
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Pregunta 1"
        assert messages[1]["role"] == "assistant"
    
    def test_get_all_conversations(self, temp_db):
        """Test: Obtener todas las conversaciones."""
        # Crear varias conversaciones
        temp_db.create_conversation("conv1", "Conv 1", "Wollok", "model1")
        temp_db.create_conversation("conv2", "Conv 2", "Haskell", "model2")
        temp_db.create_conversation("conv3", "Conv 3", "Prolog", "model3")
        
        conversations = temp_db.get_all_conversations()
        
        assert len(conversations) == 3
        assert all("conversation_id" in conv for conv in conversations)
        assert all("title" in conv for conv in conversations)
    
    def test_update_conversation_title(self, temp_db):
        """Test: Actualizar título de conversación."""
        conv_id = "test_conv_005"
        
        temp_db.create_conversation(
            conversation_id=conv_id,
            title="Old Title",
            agent_name="Wollok",
            model_name="test-model"
        )
        
        success = temp_db.update_conversation_title(conv_id, "New Title")
        
        assert success is True
        
        # Verificar que se actualizó
        info = temp_db.get_conversation_info(conv_id)
        assert info["title"] == "New Title"
    
    def test_delete_conversation(self, temp_db):
        """Test: Eliminar conversación."""
        conv_id = "test_conv_006"
        
        # Crear y agregar mensajes
        temp_db.create_conversation(
            conversation_id=conv_id,
            title="Test",
            agent_name="Wollok",
            model_name="test-model"
        )
        temp_db.add_message(conv_id, "user", "Test message")
        
        # Eliminar
        success = temp_db.delete_conversation(conv_id)
        
        assert success is True
        
        # Verificar que se eliminó
        messages = temp_db.get_conversation_messages(conv_id)
        assert len(messages) == 0

