# Customer Service

Servicio encargado de gestionar clientes, autenticación básica del MVP y validación de elegibilidad para reservas.

## Stack

- Python 3.11
- FastAPI
- SQLAlchemy
- SQLite
- RabbitMQ
- uv
- pytest / pytest-cov
- Ruff / Black / Pyright

## Alcance actual

- registro de clientes
- login con JWT
- roles básicos `customer` y `admin`
- consulta de cliente por id
- validación de elegibilidad para reservas
- cambios administrativos de estado (`ACTIVE`, `INACTIVE`, `SUSPENDED`)
- publicación de eventos del ciclo de vida del cliente

## Estructura

- `internal/` — aplicación, dominio, infraestructura e interfaz REST
- `test/` — tests unitarios e integración
- `scripts/validate.sh` — validación canónica del servicio
- `Dockerfile` — imagen local del servicio
- `docker-compose.yml` — stack local con API + RabbitMQ

## Comandos útiles

```bash
uv sync --dev
uv run ruff check .
uv run black --check .
uv run pyright
uv run pytest --cov=internal --cov-report=term-missing
./scripts/validate.sh
```

## API

Endpoints principales del MVP:

- `POST /auth/register`
- `POST /auth/login`
- `GET /customers/{customerId}`
- `GET /customers/{customerId}/reservation-eligibility`
- `PATCH /customers/{customerId}`
- `PATCH /customers/{customerId}/deactivate`
- `PATCH /customers/{customerId}/activate`
- `PATCH /customers/{customerId}/suspend`
- `PATCH /customers/{customerId}/resolve-suspension`
- `GET /customers`

## Documentación

- `docs/service-overview.md` — overview funcional y técnico del servicio
- `docs/ddd/customer-context.md` — contexto DDD relevante del servicio

## Docker local

Para desarrollo local con la configuración runtime actual, el repo incluye un `docker-compose.yml`
que levanta:

- `customer-service`
- `rabbitmq`

### Levantar el stack

```bash
docker compose up --build -d
```

### Bajar el stack

```bash
docker compose down
```

Si además querés limpiar el volumen de RabbitMQ:

```bash
docker compose down -v
```

### Variables que compose resuelve

- `CUSTOMER_SERVICE_DATABASE_URL=sqlite:///./data/customer-service.sqlite`
- `CUSTOMER_SERVICE_EVENT_PUBLISHER_BACKEND=rabbitmq`
- `CUSTOMER_SERVICE_RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/%2F`
- `CUSTOMER_SERVICE_RABBITMQ_EXCHANGE=customer.events`

### Verificación rápida

- API health: `http://localhost:8000/health`
- RabbitMQ management: `http://localhost:15672` (`guest` / `guest`)

## Notas

- La persistencia local esperada usa SQLite.
- La publicación de eventos usa RabbitMQ.
- Este repo proviene de una extracción con historia preservada desde el monorepo original.
