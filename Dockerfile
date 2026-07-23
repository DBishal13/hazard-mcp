FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

VOLUME ["/app/data"]

# MCP's stdio transport is the default -- an agent host spawns this
# container and talks to it over stdin/stdout, so there's no port to
# expose or healthcheck to poll.
CMD ["python", "-m", "hazard_mcp.server"]
