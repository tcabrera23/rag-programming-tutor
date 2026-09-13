# Supabase / RAG

Búsqueda semántica sobre las tablas `wollok`, `haskell` y `prolog` (pgvector). El cliente vive en `app/infra/rag.py`.

## RPC

Firma común:

```sql
{table}_search(
    query_embedding vector,           -- 1536 dimensiones (text-embedding-3-small)
    match_count integer DEFAULT NULL,
    filter jsonb DEFAULT '{}'
)
RETURNS TABLE(id uuid, content text, metadata jsonb, similarity double precision)
```

Funciones: `wollok_search`, `haskell_search`, `prolog_search`.

Definición (ejemplo Wollok):

```sql
CREATE OR REPLACE FUNCTION public.wollok_search(
    query_embedding vector,
    match_count integer DEFAULT NULL::integer,
    filter jsonb DEFAULT '{}'::jsonb
)
RETURNS TABLE(id uuid, content text, metadata jsonb, similarity double precision)
LANGUAGE plpgsql
AS $function$
#variable_conflict use_column
BEGIN
    RETURN query
    SELECT
        id,
        content,
        metadata,
        1 - (wollok.embedding <=> query_embedding) AS similarity
    FROM public.wollok
    WHERE (filter = '{}' OR metadata @> filter)
    ORDER BY wollok.embedding <=> query_embedding
    LIMIT match_count;
END;
$function$;
```

Repetir para `haskell` y `prolog` cambiando el nombre de tabla.

## Llamada desde Python

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

Embeddings: `openai/text-embedding-3-small` vía OpenRouter (`OPENROUTER_API_KEY`).

## Contrato RPC (no romper)

Los parámetros reales son `query_embedding`, `match_count` y opcionalmente `filter`. No existe `match_threshold`. PostgREST exige el nombre y el orden de la firma; un parámetro extra o distinto produce `PGRST202`.
