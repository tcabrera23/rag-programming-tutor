"""
Historial de conversaciones en SQLite.
Sin dependencias de Streamlit.
"""

import os
import sqlite3
from typing import Dict, List, Optional


class SQLiteDatabase:
    """Persistencia local de conversaciones y mensajes."""

    def __init__(self, db_path: str = "data/conversations.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                model_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                has_attachment BOOLEAN DEFAULT 0,
                attachment_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conv_id
            ON messages(conversation_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at
            ON conversations(created_at DESC)
        """)

        conn.commit()
        conn.close()

    def create_conversation(
        self,
        conversation_id: str,
        title: str,
        agent_name: str,
        model_name: str,
    ) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO conversations (conversation_id, title, agent_name, model_name)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, title, agent_name, model_name),
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            print(f"Error al crear conversación: {e}")
            return False

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        has_attachment: bool = False,
        attachment_type: Optional[str] = None,
    ) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO messages (conversation_id, role, content, has_attachment, attachment_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, role, content, has_attachment, attachment_type),
            )
            cursor.execute(
                """
                UPDATE conversations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al añadir mensaje: {e}")
            return False

    def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, str]]:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT role, content, has_attachment, attachment_type, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,),
            )
            messages = []
            for row in cursor.fetchall():
                message = {"role": row[0], "content": row[1]}
                if row[2]:
                    message["attachment_type"] = row[3]
                messages.append(message)
            conn.close()
            return messages
        except Exception as e:
            print(f"Error al obtener mensajes: {e}")
            return []

    def get_all_conversations(self) -> List[Dict]:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT conversation_id, title, agent_name, model_name, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC
                """
            )
            conversations = [
                {
                    "conversation_id": row[0],
                    "title": row[1],
                    "agent_name": row[2],
                    "model_name": row[3],
                    "created_at": row[4],
                    "updated_at": row[5],
                }
                for row in cursor.fetchall()
            ]
            conn.close()
            return conversations
        except Exception as e:
            print(f"Error al obtener conversaciones: {e}")
            return []

    def update_conversation_title(self, conversation_id: str, new_title: str) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = CURRENT_TIMESTAMP
                WHERE conversation_id = ?
                """,
                (new_title, conversation_id),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al actualizar título: {e}")
            return False

    def delete_conversation(self, conversation_id: str) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            cursor.execute(
                "DELETE FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al eliminar conversación: {e}")
            return False

    def get_conversation_info(self, conversation_id: str) -> Optional[Dict]:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT conversation_id, title, agent_name, model_name, created_at, updated_at
                FROM conversations
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    "conversation_id": row[0],
                    "title": row[1],
                    "agent_name": row[2],
                    "model_name": row[3],
                    "created_at": row[4],
                    "updated_at": row[5],
                }
            return None
        except Exception as e:
            print(f"Error al obtener info de conversación: {e}")
            return None
