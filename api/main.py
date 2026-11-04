"""A tiny notes API for the cloud seminar assignment.

Same HTTP contract as the seminar's reference API, written in Python instead of Go
so the reference frontend works against it unchanged.

Configuration comes from environment variables (12-factor): the same image runs
locally and in the cloud, only the values change.

    PORT         port to listen on (default 8080)
    APP_MESSAGE  text returned by GET /api/message
    APP_VERSION  which code is running; CI sets it to the commit SHA
    CORS_ORIGIN  frontend origin allowed to call this API
    DB_URL       Postgres connection string (required), never hardcoded
"""

import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from psycopg_pool import AsyncConnectionPool

# --- configuration ---------------------------------------------------------

APP_MESSAGE = os.getenv("APP_MESSAGE", "Hello from the API")
APP_VERSION = os.getenv("APP_VERSION", "dev")
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "http://localhost:3000")
DB_URL = os.getenv("DB_URL", "")

# --- logging ---------------------------------------------------------------
# One JSON line per event, to stdout: the platform (Docker, Azure) collects it.


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        if isinstance(record.args, dict):
            entry.update(record.args)
        return json.dumps(entry)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
log = logging.getLogger("api")

# --- database --------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id         BIGSERIAL PRIMARY KEY,
    text       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

pool: AsyncConnectionPool | None = None
ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the connection pool and create the table, then serve.

    Failing here is deliberate: the container exits with a clear log line instead
    of accepting traffic it cannot serve.
    """
    global pool, ready

    if not DB_URL:
        log.error("DB_URL is required")
        raise SystemExit(1)

    log.info("connecting to the database")
    try:
        pool = AsyncConnectionPool(DB_URL, min_size=1, max_size=5, open=False)
        await pool.open(wait=True, timeout=10)
        async with pool.connection() as conn:
            await conn.execute(SCHEMA)
    except Exception as err:
        log.error("cannot connect to the database", {"error": str(err)})
        raise SystemExit(1)

    ready = True
    log.info("starting API", {"cors_origin": CORS_ORIGIN, "version": APP_VERSION})
    yield

    # Fail readiness first, so the platform stops sending new requests here.
    ready = False
    log.info("shutting down")
    await pool.close()


app = FastAPI(title="Notes API", lifespan=lifespan)

# Without this the frontend works locally but fails once it lives on another domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# --- probes ----------------------------------------------------------------
# Neither probe checks the database: an outage hits every copy at once, so
# restarting them or pulling them all out of the load balancer only makes it worse.


@app.get("/livez")
async def livez():
    """Liveness: is the process alive? Failing it restarts the container."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    """Readiness: should this copy get traffic? Fails while shutting down."""
    if not ready:
        raise HTTPException(status_code=503, detail="shutting down")
    return {"status": "ok"}


# --- endpoints -------------------------------------------------------------


class NoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)


@app.get("/")
async def index():
    """A short index, so the bare URL says what this is instead of 404."""
    return {
        "service": "notes API",
        "version": APP_VERSION,
        "endpoints": [
            "/api/message",
            "/api/notes",
            "/api/notes/{id}",
            "/livez",
            "/readyz",
        ],
    }


@app.get("/api/message")
async def message():
    return {"message": APP_MESSAGE, "version": APP_VERSION}


@app.get("/api/notes")
async def list_notes():
    """Newest first, capped: a page should never pull the whole table."""
    async with pool.connection() as conn:
        rows = await (
            await conn.execute(
                "SELECT id, text, created_at FROM notes ORDER BY id DESC LIMIT 100"
            )
        ).fetchall()
    return [
        {"id": r[0], "text": r[1], "created_at": r[2].isoformat()} for r in rows
    ]


@app.post("/api/notes", status_code=201)
async def create_note(note: NoteIn):
    text = note.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text must not be blank")

    async with pool.connection() as conn:
        row = await (
            await conn.execute(
                "INSERT INTO notes (text) VALUES (%s) RETURNING id, created_at",
                (text,),
            )
        ).fetchone()
    return {"id": row[0], "text": text, "created_at": row[1].isoformat()}


@app.delete("/api/notes/{note_id}", status_code=204)
async def delete_note(note_id: int):
    """Deleting an id that is not there is a 404, not a silent success:
    the caller asked to remove something that never existed."""
    async with pool.connection() as conn:
        cur = await conn.execute("DELETE FROM notes WHERE id = %s", (note_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="note not found")
