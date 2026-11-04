# Cloud Seminar Assignment — Notes app

Three services that talk to each other, deployed to Azure:

```
web/   React (Vite) frontend  → static files → Blob Storage static website
api/   Python REST API        → container    → Azure Container Apps
                              → managed resource: Azure Database for PostgreSQL
```

The frontend is the seminar's reference one, which the assignment allows. The API
is written from scratch in **Python (FastAPI)**, since the assignment rules out Go.

## The API

| Endpoint | Does |
|---|---|
| `GET /api/message` | `{"message": "<APP_MESSAGE>", "version": "<APP_VERSION>"}` |
| `GET /api/notes` | The 100 newest notes |
| `POST /api/notes` | Adds a note: `{"text": "..."}` |
| `DELETE /api/notes/{id}` | Removes a note; 404 if that id is not there |
| `GET /livez` | Liveness probe: 200 while the process runs |
| `GET /readyz` | Readiness probe: 200, or 503 while shutting down |

All configuration comes from environment variables, so the same image runs locally
and in the cloud:

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `8080` | Port to listen on |
| `APP_MESSAGE` | `Hello from the API` | Text returned by `/api/message` |
| `APP_VERSION` | `dev` | Which code is running; CI sets it to the commit SHA |
| `CORS_ORIGIN` | `http://localhost:3000` | Frontend origin allowed to call the API |
| `DB_URL` | (required) | `postgres://user:password@host:5432/db` |

`DB_URL` carries a password: it is never committed and never baked into the image.
Locally it comes from `compose.yaml`; in the cloud it is a Container App secret.

## Run it locally

```bash
docker compose up --build    # web on http://localhost:3000, API on :8081, Postgres inside
docker compose down          # stop; notes are kept in the "dbdata" volume
docker compose down -v       # stop and delete the volume: notes are gone
```

The database publishes no port: only the API can reach it, over the Compose network.

## The images

Both are multi-stage and run as a non-root user:

- **api**: dependencies are installed into a virtualenv in the first stage; the final
  image carries only that virtualenv and `main.py`, with no pip cache and no build tools.
- **web**: Node builds the static files, nginx (unprivileged) serves them.
