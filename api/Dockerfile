# Two stages: the first installs the dependencies, the second contains only
# the virtualenv and the app. No pip cache and no build tools in the final image.

# ---------- Stage 1: build ----------
FROM python:3.13-slim AS build
WORKDIR /src

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Dependencies first: this layer is cached until requirements.txt changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ---------- Stage 2: run ----------
FROM python:3.13-slim

# A non-root user: if the process is compromised it owns nothing.
RUN useradd --system --uid 10001 --no-create-home appuser

COPY --from=build /venv /venv
ENV PATH="/venv/bin:$PATH"

WORKDIR /app
# Then the code, which changes often.
COPY main.py ./

# Which code is this? CI passes the commit SHA; shown in /api/message.
ARG VERSION=dev
ENV APP_VERSION=$VERSION

USER appuser
EXPOSE 8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
