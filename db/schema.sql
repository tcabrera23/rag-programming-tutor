-- ChatPdeP RAG: solo tablas de teoría (wollok / haskell / prolog).
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS wollok (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content text NOT NULL,
    metadata jsonb,
    embedding vector(1536)
);

CREATE TABLE IF NOT EXISTS haskell (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content text NOT NULL,
    metadata jsonb,
    embedding vector(1536)
);

CREATE TABLE IF NOT EXISTS prolog (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content text NOT NULL,
    metadata jsonb,
    embedding vector(1536)
);

CREATE INDEX IF NOT EXISTS wollok_embedding_idx
    ON wollok USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS haskell_embedding_idx
    ON haskell USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS prolog_embedding_idx
    ON prolog USING hnsw (embedding vector_cosine_ops);

CREATE OR REPLACE FUNCTION public.wollok_search(
    query_embedding vector,
    match_count integer DEFAULT NULL::integer,
    filter jsonb DEFAULT '{}'::jsonb
)
RETURNS TABLE(
    id uuid,
    content text,
    metadata jsonb,
    similarity double precision
)
LANGUAGE plpgsql
AS $function$
#variable_conflict use_column
BEGIN
    RETURN query
    SELECT
        wollok.id,
        wollok.content,
        wollok.metadata,
        1 - (wollok.embedding <=> query_embedding) AS similarity
    FROM public.wollok
    WHERE (filter = '{}'::jsonb OR wollok.metadata @> filter)
    ORDER BY wollok.embedding <=> query_embedding
    LIMIT match_count;
END;
$function$;

CREATE OR REPLACE FUNCTION public.haskell_search(
    query_embedding vector,
    match_count integer DEFAULT NULL::integer,
    filter jsonb DEFAULT '{}'::jsonb
)
RETURNS TABLE(
    id uuid,
    content text,
    metadata jsonb,
    similarity double precision
)
LANGUAGE plpgsql
AS $function$
#variable_conflict use_column
BEGIN
    RETURN query
    SELECT
        haskell.id,
        haskell.content,
        haskell.metadata,
        1 - (haskell.embedding <=> query_embedding) AS similarity
    FROM public.haskell
    WHERE (filter = '{}'::jsonb OR haskell.metadata @> filter)
    ORDER BY haskell.embedding <=> query_embedding
    LIMIT match_count;
END;
$function$;

CREATE OR REPLACE FUNCTION public.prolog_search(
    query_embedding vector,
    match_count integer DEFAULT NULL::integer,
    filter jsonb DEFAULT '{}'::jsonb
)
RETURNS TABLE(
    id uuid,
    content text,
    metadata jsonb,
    similarity double precision
)
LANGUAGE plpgsql
AS $function$
#variable_conflict use_column
BEGIN
    RETURN query
    SELECT
        prolog.id,
        prolog.content,
        prolog.metadata,
        1 - (prolog.embedding <=> query_embedding) AS similarity
    FROM public.prolog
    WHERE (filter = '{}'::jsonb OR prolog.metadata @> filter)
    ORDER BY prolog.embedding <=> query_embedding
    LIMIT match_count;
END;
$function$;
