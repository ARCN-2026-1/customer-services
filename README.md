# Customer Service

Servicio encargado de gestionar clientes, autenticación básica del MVP y validación de elegibilidad para reservas.

## Stack

- Python 3.11
- FastAPI
- SQLAlchemy
- MySQL 8 + Alembic
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
- `docker-compose.yml` — stack local con API + MySQL + RabbitMQ
- `alembic/` + `alembic.ini` — migraciones del esquema `customer-service`

## Comandos útiles

```bash
uv sync --dev
uv run ruff check .
uv run black --check .
uv run pyright
uv run pytest --cov=internal --cov-report=term-missing
uv run alembic upgrade head
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

### Mapa rápido

| Documento | Cuándo leerlo | Qué cubre |
| --- | --- | --- |
| `docs/service-overview.md` | Primer contacto / onboarding | panorama funcional, límites y responsabilidades del servicio |
| `docs/services/customer-service.md` | Trabajo diario sobre el servicio | endpoints, eventos, dependencias runtime, diagramas y operación local |
| `docs/services/integration-map.md` | Integraciones entre microservicios | contratos REST/RabbitMQ y relación con otros servicios |
| `docs/ddd/customer-context.md` | Modelo de dominio actual | aggregate root, invariantes, casos de uso y eventos del contexto |

### Orden sugerido

1. `docs/service-overview.md`
2. `docs/services/customer-service.md`
3. `docs/services/integration-map.md`
4. `docs/ddd/customer-context.md`

## Docker local

Para desarrollo local con la configuración runtime actual, el repo incluye:

- `docker-compose.yml` — compose base orientado a la app `customer-service`
- `docker-compose.dev.yml` — overrides para dependencias locales y puertos de desarrollo

Usados juntos levantan:

- `customer-service`
- `mysql`
- `rabbitmq`

### Bootstrap de schema local

Antes de usar la API contra MySQL, corré las migraciones del servicio:

```bash
uv run alembic upgrade head
```

El schema usa charset `utf8mb4` y collation `utf8mb4_0900_ai_ci`.

### Levantar el stack

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Bajar el stack

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

Si además querés limpiar el volumen de RabbitMQ:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

### Variables que compose resuelve

Cuando usás ambos archivos (`docker-compose.yml` + `docker-compose.dev.yml`), `customer-service` recibe:

- `CUSTOMER_SERVICE_DATABASE_URL=mysql+pymysql://customer_app:customer_app_secret@mysql:3306/customer_service?charset=utf8mb4`
- `CUSTOMER_SERVICE_EVENT_PUBLISHER_BACKEND=rabbitmq`
- `CUSTOMER_SERVICE_RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/%2F`
- `CUSTOMER_SERVICE_RABBITMQ_EXCHANGE=customer.events`

### Verificación rápida

- API health: `http://localhost:8000/health`
- MySQL: `localhost:3306` (`customer_app` / `customer_app_secret`, schema `customer_service`)
- RabbitMQ management: `http://localhost:15672` (`guest` / `guest`)

## Notas

- La persistencia local esperada usa MySQL con un schema dedicado para `customer-service`.
- Las migraciones se gestionan con Alembic; la app NO crea tablas en runtime.
- La publicación de eventos usa RabbitMQ.
- Este repo proviene de una extracción con historia preservada desde el monorepo original.
