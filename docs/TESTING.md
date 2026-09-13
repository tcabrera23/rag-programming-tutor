# Tests

Requiere `.env` con `OPENROUTER_API_KEY`, `SUPABASE_URL` y `SUPABASE_ANON_KEY` para tests que pegan a APIs. Los tests de agentes y SQLite corren sin keys.

```bash
pip install -r requirements.txt
pytest tests/ -v
```

En PowerShell, scripts locales van con `.\` (`.\venv\Scripts\python.exe -m pytest tests -v`).

## Qué cubre

| Archivo | Qué |
|---|---|
| `test_agents_config.py` | Prompts y config de los 3 agentes |
| `test_database.py` | CRUD SQLite |
| `test_rag_tool.py` | Cliente RAG y tool `recuperar_teoria` |
| `test_file_extraction.py` | PDF e imágenes |
| `test_integration.py` | RAG + LLM + RPC |
| `test_llm_judge.py` | Calidad de respuesta (LLM-as-a-Judge) |

Markers: `unit`, `integration`, `slow`, `judge`, `database`, `rag`.

```bash
pytest tests/ -m unit -v
pytest tests/test_llm_judge.py -v
```

Si un test de RAG/LLM se skippea, falta una key en `.env` (usar `SUPABASE_ANON_KEY`, no `SERVICE_KEY`).
