"""
Exporta wollok / haskell / prolog desde Supabase a db/seed.sql.gz.
No exporta chatpdep_tokens ni otras tablas.

Uso (con .env local, no se commitea):
    python scripts/export_rag_seed.py
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

ROOT = Path(__file__).resolve().parents[1]
TABLES = ("wollok", "haskell", "prolog")
PAGE = 200


def _vector_literal(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return "[" + ",".join(str(float(x)) for x in value) + "]"


def _fetch_table(client, table: str) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        end = start + PAGE - 1
        resp = (
            client.table(table)
            .select("id,content,metadata,embedding")
            .range(start, end)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < PAGE:
            break
        start += PAGE
    return rows


def _copy_block(table: str, rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(
        buf,
        delimiter="\t",
        lineterminator="\n",
        quoting=csv.QUOTE_MINIMAL,
        doublequote=True,
    )
    for row in rows:
        metadata = row.get("metadata")
        if metadata is None:
            meta_s = r"\N"
        else:
            meta_s = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
        embedding = _vector_literal(row.get("embedding"))
        if not embedding:
            continue
        writer.writerow(
            [
                str(row["id"]),
                row.get("content") or "",
                meta_s,
                embedding,
            ]
        )
    body = buf.getvalue()
    return (
        f"COPY {table} (id, content, metadata, embedding) FROM stdin "
        f"WITH (FORMAT csv, DELIMITER E'\\t', NULL '\\N', QUOTE '\"');\n"
        f"{body}\\.\n\n"
    )


def main() -> int:
    load_dotenv(ROOT / ".env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("Faltan SUPABASE_URL y SUPABASE_ANON_KEY en .env", file=sys.stderr)
        return 1

    client = create_client(url, key)
    out_dir = ROOT / "db"
    out_dir.mkdir(exist_ok=True)
    sql_path = out_dir / "seed.sql.gz"

    chunks = ["BEGIN;\n", "SET client_encoding = 'UTF8';\n\n"]
    for table in TABLES:
        rows = _fetch_table(client, table)
        print(f"{table}: {len(rows)} filas")
        chunks.append(f"TRUNCATE {table};\n")
        chunks.append(_copy_block(table, rows))
    chunks.append("COMMIT;\n")

    with gzip.open(sql_path, "wt", encoding="utf-8", newline="\n") as fh:
        fh.write("".join(chunks))
    print(f"Escrito {sql_path} ({sql_path.stat().st_size} bytes gzip)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
