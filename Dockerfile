FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    PATH=${PATH}:/root/.local/bin/

EXPOSE 8000

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN apt-get update && apt-get install -y \
    curl wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /app/src/server/liftover_data \
    && wget -O /app/src/server/liftover_data/liftOver \
    http://hgdownload.cse.ucsc.edu/admin/exe/linux.x86_64/liftOver \
    && chmod +x /app/src/server/liftover_data/liftOver \
    && curl -LsSf https://astral.sh/uv/install.sh | sh 
    
RUN uv sync --no-dev

CMD ["uv", "run", "fastmcp", "run", "src/server/mcp_server.py", "--transport", "sse", "--host", "0.0.0.0", "--port", "8000"]