# RAG (Postgres + pgvector)

El corpus vive en tres tablas: `wollok`, `haskell`, `prolog`. Schema: [`db/schema.sql`](../db/schema.sql). Datos: [`db/seed.sql.gz`](../db/seed.sql.gz) (~1100 chunks, embeddings `vector(1536)` de `openai/text-embedding-3-small`).

No hace falta una cuenta de Supabase para correr el tutor. Docker Compose levanta `pgvector/pgvector:pg16` y carga schema + seed al crear el volumen.

```bash
docker compose up -d postgres
# DATABASE_URL=postgresql://chatpdep:chatpdep@localhost:5432/chatpdep
```

Reseed (borra el volumen):

```bash
docker compose down -v
docker compose up -d postgres
```

## Búsqueda

Mismas funciones que el RPC original:

```sql
{table}_search(query_embedding vector, match_count integer, filter jsonb DEFAULT '{}')
RETURNS (id uuid, content text, metadata jsonb, similarity double precision)
```

`similarity = 1 - (embedding <=> query)`. Índice HNSW con `vector_cosine_ops`.

Desde Python:

```python
from app.infra.rag import get_rag_instance

rag = get_rag_instance()
results = rag.search_theory(
    query="¿Qué es un objeto en Wollok?",
    table_name="wollok",
    query_name="wollok_search",
    match_count=5,
)
```

`app/infra/rag.py` habla por `DATABASE_URL` (psycopg). Sigue haciendo embed de la query con OpenRouter.

## Recrear en un Postgres / Supabase propio

Aplicá `db/schema.sql` y restaurá el seed:

```bash
gunzip -c db/seed.sql.gz | psql "$DATABASE_URL"
```

No copies un proyecto compartido de demos: este dump es solo las tres tablas de teoría.

Para regenerar el gzip (no es parte del runtime): `python scripts/export_rag_seed.py` contra un Postgres/Supabase que ya tenga las tres tablas. El script no se commitea con keys.
