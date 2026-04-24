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
- `docker-compose.yml` — compose base de despliegue para runtime completo (`customer-migration`, `customer-service`, `customer-worker`)
- `docker-compose.dev.yml` — overlay local con MySQL + RabbitMQ
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

## Docker

### Deploy / servidor (runtime del servicio)

`docker-compose.yml` define una configuración base orientada a despliegue del runtime completo del servicio.

Incluye:

- job de migraciones `customer-migration` (one-shot)
- API HTTP `customer-service`
- worker RabbitMQ `customer-worker` (`consumer.py`)
- política de reinicio (`unless-stopped`)
- variables runtime vía placeholders (`CUSTOMER_SERVICE_*`, `MYSQL_*`, `RABBITMQ_*`)
- mapeo de puerto configurable (`${CUSTOMER_SERVICE_PORT:-8000}:8000`)
- healthcheck HTTP sobre `/health`
- orden de arranque: API y worker esperan a que `customer-migration` termine en éxito

Ejemplo usando archivo de entorno no versionado:

```bash
docker compose --env-file .env.deploy -f docker-compose.yml up -d
```

### Local development

Para desarrollo local con infraestructura incluida, el repo usa composición de archivos:

- `docker-compose.yml` — base runtime (`customer-migration`, `customer-service`, `customer-worker`) usada en deploy
- `docker-compose.dev.yml` — overlay local para infraestructura, `depends_on` y puertos de dev
- `.env.local` — variables de desarrollo local para MySQL y RabbitMQ del stack dev
- `.env.deploy` — variables para despliegue con infraestructura externa

Usados juntos levantan:

- `customer-migration`
- `customer-service`
- `customer-worker`
- `mysql`
- `rabbitmq`

`customer-migration` corre `alembic upgrade head` automáticamente dentro del compose.

El schema usa charset `utf8mb4` y collation `utf8mb4_0900_ai_ci`.

### Levantar el stack

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Bajar el stack

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml down
```

Si además querés limpiar el volumen de RabbitMQ:

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml down -v
```

### Variables que compose resuelve

Cuando usás ambos archivos (`docker-compose.yml` + `docker-compose.dev.yml`), `customer-migration`, `customer-service` y `customer-worker` reciben el mismo bloque runtime:

- `CUSTOMER_SERVICE_EVENT_PUBLISHER_BACKEND=${CUSTOMER_SERVICE_EVENT_PUBLISHER_BACKEND:-rabbitmq}`
- `CUSTOMER_SERVICE_JWT_SECRET=${CUSTOMER_SERVICE_JWT_SECRET:-local-dev-secret}`
- `MYSQL_HOST=mysql`
- `MYSQL_DATABASE=${MYSQL_DATABASE:-customer_service}`
- `MYSQL_USER=${MYSQL_USER:-customer_app}`
- `MYSQL_PASSWORD=${MYSQL_PASSWORD:-customer_app_local}`
- `MYSQL_LOCAL_PORT=${MYSQL_LOCAL_PORT:-3306}`
- `RABBITMQ_HOST=rabbitmq`
- `RABBITMQ_DEFAULT_USER=${RABBITMQ_DEFAULT_USER:-guest}`
- `RABBITMQ_DEFAULT_PASS=${RABBITMQ_DEFAULT_PASS:-guest}`
- `RABBITMQ_PORT=${RABBITMQ_PORT:-5672}`
- `RABBITMQ_UI_PORT=${RABBITMQ_UI_PORT:-15672}`
- `CUSTOMER_SERVICE_RABBITMQ_REQUEST_EXCHANGE=customer.exchange`
- `CUSTOMER_SERVICE_RABBITMQ_REQUEST_EXCHANGE_TYPE=direct`
- `CUSTOMER_SERVICE_RABBITMQ_REQUEST_ROUTING_KEY=customer.request`
- `CUSTOMER_SERVICE_RABBITMQ_RESPONSE_EXCHANGE=customer.exchange`
- `CUSTOMER_SERVICE_RABBITMQ_RESPONSE_EXCHANGE_TYPE=direct`
- `CUSTOMER_SERVICE_RABBITMQ_RESPONSE_ROUTING_KEY=customer.response.key`

En deploy podés optar por URLs directas (`CUSTOMER_SERVICE_DATABASE_URL`, `CUSTOMER_SERVICE_RABBITMQ_URL`) o por variables desglosadas (`MYSQL_*`, `RABBITMQ_*`).

Además, MySQL local usa `MYSQL_ROOT_PASSWORD` (solo infraestructura local).

El repo incluye `.env.example` con placeholders seguros. Además, este repo mantiene separados:

- `.env.local` para desarrollo local
- `.env.deploy` para despliegue

Las variables de contrato RabbitMQ también quedan explícitas en esos archivos para evitar depender solo de defaults implícitos.

El `.env.local` de desarrollo usa valores como estos:

```env
MYSQL_DATABASE=customer_service
MYSQL_USER=customer_app
MYSQL_PASSWORD=customer_app_local
MYSQL_ROOT_PASSWORD=root_local
MYSQL_LOCAL_PORT=3306
RABBITMQ_DEFAULT_USER=guest
RABBITMQ_DEFAULT_PASS=guest
RABBITMQ_PORT=5672
RABBITMQ_UI_PORT=15672
```

### Verificación rápida

- API health: `http://localhost:8000/health`
- MySQL: `localhost:${MYSQL_LOCAL_PORT:-3306}` (credenciales definidas por tus variables locales)
- RabbitMQ management: `http://localhost:${RABBITMQ_UI_PORT:-15672}` (credenciales definidas por tus variables locales)
- Worker activo: logs del consumer con `docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml logs -f customer-worker`

## Notas

- La persistencia local esperada usa MySQL con un schema dedicado para `customer-service`.
- Las migraciones se gestionan con Alembic; la app NO crea tablas en runtime.
- La publicación de eventos usa RabbitMQ.
- Este repo proviene de una extracción con historia preservada desde el monorepo original.
