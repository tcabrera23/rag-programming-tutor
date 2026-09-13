# Tests

Los tests de agentes y SQLite corren sin keys. RAG/LLM necesitan `OPENROUTER_API_KEY` y `DATABASE_URL` (Postgres con seed).

```bash
pip install -r requirements.txt
docker compose up -d postgres
pytest tests/ -v
```

En PowerShell: `.\venv\Scripts\python.exe -m pytest tests -v`.

## E2E (Playwright)

La UI de conversaciones se prueba en Chromium. El server arranca con `CHATPDP_E2E=1` (echo sin LLM) y un SQLite temporal (`CHATPDP_DB_PATH`), así no toca `data/conversations.db` ni pide API keys.

```bash
pip install -r requirements.txt
playwright install chromium
pytest tests/e2e -m e2e -v
```

## Qué cubre

| Archivo | Qué |
|---|---|
| `test_agents_config.py` | Prompts y config de los 3 agentes |
| `test_database.py` | CRUD SQLite |
| `test_rag_tool.py` | Cliente RAG y tool `recuperar_teoria` |
| `test_file_extraction.py` | PDF e imágenes |
| `test_integration.py` | RAG + LLM + Postgres |
| `test_llm_judge.py` | Calidad de respuesta (LLM-as-a-Judge) |
| `e2e/test_conversations_ui.py` | Historial, nueva conversación, selectores |

Markers: `unit`, `integration`, `slow`, `judge`, `database`, `rag`, `e2e`.
