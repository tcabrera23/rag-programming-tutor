# Seguridad

El RAG corre contra Postgres local (`DATABASE_URL`). El seed del repo es teoría de PdeP, no conversaciones de usuarios.

No commitear `.env` ni `.streamlit/secrets.toml`. La password de Docker (`chatpdep/chatpdep`) es solo para desarrollo local.

## Métricas opcionales

`app/infra/tracking.py` puede escribir en `chatpdep_tokens` si definís `SUPABASE_URL` + `SUPABASE_ANON_KEY`. Sin esas variables, el tracking queda deshabilitado. No uses la service role en la app.

Si montás las tablas de teoría en un Supabase propio, habilitá RLS y limitá `anon` a `SELECT` en `wollok` / `haskell` / `prolog`.
