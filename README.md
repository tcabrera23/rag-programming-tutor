# ChatPdeP

Tutor de Paradigmas de Programación (UTN FRBA). Tres agentes (Wollok, Haskell, Prolog) con RAG sobre Postgres + pgvector.

Dos entradas:

- **Streamlit** — chat en el navegador
- **FastAPI** — API compatible con OpenAI (Cursor, VS Code, etc.)

Ambas llaman al mismo turno de chat. El corpus de teoría (Wollok / Haskell / Prolog) viene en `db/`.

## Arquitectura

```
streamlit_app.py          UI Streamlit
app/                      backend del agente
  main.py                 factory FastAPI
  delivery/               HTTP (routers)
  services/               orquestación del turno
  domain/                 prompts y tools
  infra/                  SQLite, RAG (Postgres), LLMs
db/                       schema + seed pgvector
tests/
docs/
```

```
Streamlit ──┐
            ├──► app.services.chat ──► domain + infra
FastAPI  ───┘                              │
                                           ▼
                                    Postgres pgvector
```

## Quickstart

```bash
cp .env.example .env   # GROQ_API_KEY y OPENROUTER_API_KEY
pip install -r requirements.txt
docker compose up -d postgres
streamlit run streamlit_app.py
```

API (docs en http://localhost:8000/docs):

```bash
uvicorn app.main:app --reload --port 8000
```

Stack completo (UI + API + Postgres + Ollama):

```bash
docker compose up --build
```

Sin GPU: `docker compose -f docker-compose.cpu.yml up --build`

El seed se carga **solo la primera vez** (volumen vacío). Para recargarlo: `docker compose down -v`.

## Variables de entorno

| Variable | Uso |
|---|---|
| `GROQ_API_KEY` | Groq (gratis, proveedor por defecto) |
| `OPENROUTER_API_KEY` | Embeddings RAG y modelos cloud |
| `DATABASE_URL` | Postgres local (`postgresql://chatpdep:chatpdep@localhost:5432/chatpdep`) |
| `OLLAMA_BASE_URL` | Modelos locales (`http://localhost:11434`) |

Plantilla: `.env.example`. Keys de Groq: [console.groq.com](https://console.groq.com/keys).

## API / Cursor

Modo A (recomendado) — un proveedor por agente:

- Wollok: `http://localhost:8000/v1/wollok`
- Haskell: `http://localhost:8000/v1/haskell`
- Prolog: `http://localhost:8000/v1/prolog`

El campo `model` del request es el LLM (`groq/compound`, `openai/gpt-4o`, …).

Modo B — un solo proveedor: base URL `http://localhost:8000/v1`, modelos `chatpdep-wollok`, `chatpdep-haskell`, `chatpdep-prolog` (opcional `:llm-id`).

Health: `GET /health`.

## Anexos

- [RAG / Postgres](docs/supabase.md)
- [Seguridad](docs/security.md)
- [Tests](docs/testing.md)
- [Changelog](CHANGELOG.md)
