FROM python:3.11-slim

# Instalamos uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Configuración de entorno
ENV UV_SYSTEM_PYTHON=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOME=/tmp
ENV UV_CACHE_DIR=/tmp/uv-cache

WORKDIR /app

RUN mkdir -p /tmp/uv-cache

# Dependencias
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-dev

# Código fuente
COPY . .

# Exponer puerto de Customer API
EXPOSE 8001

# Comando por defecto para la API
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
