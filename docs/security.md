# Seguridad (RLS)

La app usa `SUPABASE_ANON_KEY` (no la service role) para RAG y métricas. El alcance lo definen las políticas RLS.

## Por qué

La service key bypassa RLS. Si se filtra, hay acceso total. El anon key solo puede lo que las políticas permiten.

## Políticas

Tablas de teoría (`wollok`, `haskell`, `prolog`): lectura pública para RAG.

```sql
CREATE POLICY "Permitir lectura pública en wollok"
ON wollok FOR SELECT USING (true);
```

Igual para `haskell` y `prolog`. RLS debe estar habilitado en cada tabla.

Tabla `chatpdep_tokens`: inserción pública, lectura autenticada.

```sql
CREATE POLICY "Permitir inserción pública en chatpdep_tokens"
ON chatpdep_tokens FOR INSERT WITH CHECK (true);

CREATE POLICY "Permitir lectura autenticada en chatpdep_tokens"
ON chatpdep_tokens FOR SELECT
USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
```

## Código

`app/infra/rag.py` y `app/infra/tracking.py` leen `SUPABASE_ANON_KEY` y caen a `SUPABASE_SERVICE_KEY` solo por retrocompatibilidad. No commitear `.env` ni `.streamlit/secrets.toml`.
