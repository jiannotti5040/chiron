# Chiron engine endpoint — request in, certificate out, source never serialized.
# Build context is the vault root; .dockerignore limits it to Primus/ only.
FROM python:3.12-slim

WORKDIR /app
COPY Primus/ /app/Primus/

# numpy is used by the engine; the endpoint itself is stdlib. gplearn is left
# OUT on purpose: without it the /conjecture tool honestly REFUSES when the
# exact engine abstains, and the image stays small enough for a free instance.
RUN pip install --no-cache-dir numpy && pip install --no-cache-dir ./Primus

# Local default 8790; Render (and any PaaS) injects $PORT, which the CMD binds.
EXPOSE 8790
CMD ["sh", "-c", "python3 -m primus.engine_server --host 0.0.0.0 --port ${PORT:-8790}"]
