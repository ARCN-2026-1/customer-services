# Customer Service

## Propósito

Gestionar clientes y su estado dentro del sistema. En el MVP actual, este servicio también resuelve la autenticación básica del usuario, por lo que `Customer` representa tanto al cliente del negocio como al usuario autenticable del sistema.

## Alcance del MVP

Además del modelo del dominio definido en el DDD, este servicio incorpora decisiones técnicas para poder operar como MVP funcional:

- registro con email y contraseña
- login con JWT de corta duración
- roles básicos: `customer` y `admin`
- validación de elegibilidad para reserva

Estas decisiones responden a necesidades del MVP y no implican necesariamente la forma final del dominio a largo plazo.

## Límites del servicio

### Este servicio sí hace

- registrar clientes
- autenticar clientes
- mantener estado y datos del cliente
- validar si un cliente puede reservar
- publicar eventos del ciclo de vida del cliente

### Este servicio no hace

- gestionar reservas
- procesar pagos
- decidir reglas internas de Booking
- consumir eventos entrantes en el MVP
- implementar refresh tokens o revocación compleja

## Responsabilidades

- registrar clientes con email y contraseña
- autenticar clientes mediante login
- emitir JWT de corta duración
- mantener el estado del cliente
- actualizar datos del cliente
- activar clientes inactivos
- suspender clientes activos
- resolver suspensiones de clientes
- exponer consulta de elegibilidad para reserva
- publicar eventos relevantes del ciclo de vida del cliente

## Casos de uso

### Públicos para otros servicios

- `GetCustomerById`
- `ValidateCustomerForReservation`

### Públicos para autenticación

- `RegisterCustomer`
- `AuthenticateCustomer`

### Administrativos

- `UpdateCustomer`
- `DeactivateCustomer`
- `ActivateCustomer`
- `SuspendCustomer`
- `ResolveCustomerSuspension`
- `ListCustomers`

## Endpoints

### Resumen rápido

| Método | Ruta | Tipo | Auth |
| --- | --- | --- | --- |
| `POST` | `/auth/register` | Público | No |
| `POST` | `/auth/login` | Público | No |
| `GET` | `/customers/{customerId}` | Consulta | No |
| `GET` | `/customers/{customerId}/reservation-eligibility` | Integración interna | No |
| `PATCH` | `/customers/{customerId}` | Administrativo | Bearer admin |
| `PATCH` | `/customers/{customerId}/deactivate` | Administrativo | Bearer admin |
| `PATCH` | `/customers/{customerId}/activate` | Administrativo | Bearer admin |
| `PATCH` | `/customers/{customerId}/suspend` | Administrativo | Bearer admin |
| `PATCH` | `/customers/{customerId}/resolve-suspension` | Administrativo | Bearer admin |
| `GET` | `/customers` | Administrativo | Bearer admin |

### Autenticación

#### Registrar cliente

```http
POST /auth/register
```

Body esperado:

```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "+57-3000000000",
  "password": "plain-password"
}
```

#### Login

```http
POST /auth/login
```

Body esperado:

```json
{
  "email": "jane@example.com",
  "password": "plain-password"
}
```

Respuesta esperada:

```json
{
  "accessToken": "jwt-token",
  "tokenType": "Bearer",
  "expiresIn": 1800,
  "customer": {
    "customerId": "uuid",
    "name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "+57-3000000000",
    "status": "ACTIVE",
    "role": "customer"
  }
}
```

### Consultas

#### Obtener cliente por identificador

```http
GET /customers/{customerId}
```

#### Validar cliente para reserva

```http
GET /customers/{customerId}/reservation-eligibility
```

Respuesta esperada:

```json
{
  "customerId": "uuid",
  "status": "ACTIVE",
  "isEligible": true
}
```

### Administración

Todos los endpoints administrativos requieren autenticación Bearer con rol `admin`.

```http
PATCH /customers/{customerId}
PATCH /customers/{customerId}/deactivate
PATCH /customers/{customerId}/activate
PATCH /customers/{customerId}/suspend
PATCH /customers/{customerId}/resolve-suspension
GET /customers
```

## Errores relevantes

- `401 Unauthorized` — credenciales inválidas, falta token Bearer o token inválido
- `403 Forbidden` — token válido pero sin rol `admin`
- `409 Conflict` — email duplicado o transición de estado inválida
- `404 Not Found` — customer no encontrado
- `503 Service Unavailable` — fallo al publicar un evento de integración
- `500 Internal Server Error` — error inesperado no controlado dentro del runtime HTTP

## Logging

El servicio tiene logging básico con la librería estándar de Python.

En términos generales, cubre:

- intentos y éxitos de `register/login`
- cambios de estado administrativos del cliente
- fallos al publicar eventos hacia RabbitMQ
- errores inesperados capturados por el handler global `500 Internal Server Error`

No loguea contraseñas ni expone secretos deliberadamente.

## Puertos

### Puertos de entrada

- `RegisterCustomerUseCase`
- `AuthenticateCustomerUseCase`
- `GetCustomerByIdUseCase`
- `ValidateCustomerForReservationUseCase`
- `UpdateCustomerUseCase`
- `DeactivateCustomerUseCase`
- `ActivateCustomerUseCase`
- `SuspendCustomerUseCase`
- `ResolveCustomerSuspensionUseCase`
- `ListCustomersUseCase`

### Puertos de salida

- `CustomerRepository`
- `EventPublisher`
- `PasswordHasher`
- `TokenGenerator`

## Adaptadores

### Adaptadores de entrada

- controlador REST para autenticación
- controlador REST para consultas de cliente
- controlador REST para administración de cliente

### Adaptadores de salida

- adaptador de persistencia SQLite
- adaptador de publicación de eventos
- adaptador de hash de contraseña
- adaptador de generación de JWT

## Estados del cliente

- `ACTIVE`
- `INACTIVE`
- `SUSPENDED`

## Reglas de transición

- `DeactivateCustomer` solo aplica desde `ACTIVE`
- `ActivateCustomer` solo aplica desde `INACTIVE`
- `SuspendCustomer` solo aplica desde `ACTIVE`
- `ResolveCustomerSuspension` solo aplica desde `SUSPENDED`
- `INACTIVE` y `SUSPENDED` implican que el cliente no es elegible para reservar

## Eventos que publica

### `CustomerRegistered`

Se publica al registrar un cliente exitosamente.

```json
{
  "customerId": "uuid",
  "name": "Jane Doe",
  "email": "jane@example.com",
  "registeredAt": "timestamp"
}
```

### `CustomerInfoUpdated`

Se publica al actualizar datos del cliente.

```json
{
  "customerId": "uuid",
  "updatedFields": ["name", "phone"]
}
```

### `CustomerDeactivated`

Se publica al desactivar un cliente activo.

```json
{
  "customerId": "uuid",
  "deactivatedAt": "timestamp",
  "reason": "manual"
}
```

### `CustomerActivated`

Se publica al activar un cliente inactivo.

```json
{
  "customerId": "uuid",
  "activatedAt": "timestamp"
}
```

### `CustomerSuspended`

Se publica al suspender un cliente activo.

```json
{
  "customerId": "uuid",
  "suspendedAt": "timestamp",
  "reason": "policy_violation"
}
```

### `CustomerSuspensionResolved`

Se publica al resolver la suspensión de un cliente suspendido.

```json
{
  "customerId": "uuid",
  "resolvedAt": "timestamp"
}
```

## Eventos que consume

Por ahora no hay eventos obligatorios de entrada para el MVP.

## Reglas de negocio relevantes

- el email debe ser único en el sistema
- el nombre y email son obligatorios
- `passwordHash` nunca debe exponerse por la API
- un cliente `INACTIVE` o `SUSPENDED` no puede crear nuevas reservas
- la validación de elegibilidad para reserva debe responder en tiempo real
- no se puede eliminar un cliente con reservas activas; el camino correcto es desactivar o suspender según corresponda

## Integración con Booking

### Relación

- Booking consulta si el cliente está habilitado para reservar
- Booking consulta datos básicos del cliente
- Booking reacciona a `CustomerDeactivated`
- Booking puede reaccionar también a `CustomerSuspended` si la política de negocio futura lo requiere

### Contrato interno

La consulta de elegibilidad (`/customers/{customerId}/reservation-eligibility`) forma parte de la integración interna entre servicios.
No depende del JWT del usuario final.

### Comunicación

- **síncrona:** consulta de datos y elegibilidad vía REST
- **asíncrona:** publicación de cambios de estado del cliente mediante eventos RabbitMQ

## Observaciones de diseño

- en este MVP, `Customer` unifica perfil de negocio y autenticación por simplicidad
- si el sistema crece, identidad y autenticación pueden separarse a otro contexto o servicio
- la auth del MVP no incluye refresh tokens ni revocación compleja
- los roles básicos del MVP son `customer` y `admin`
- la base de datos SQLite del servicio se almacena en `services/customer-service/data/customer-service.sqlite`
- el servicio publica eventos mediante RabbitMQ y no consume eventos entrantes en el MVP

## Validación técnica

- tests: `uv run pytest`
- type checking: `uv run pyright`
- formato: `uv run black --check .`
- lint: `uv run ruff check .`
- validación canónica del servicio: desde `services/customer-service/`, ejecutar `./scripts/validate.sh`
- integración real RabbitMQ: `uv run pytest test/integration/test_rabbitmq_event_publisher.py -vv`
  - el test usa Docker + Testcontainers para levantar un broker RabbitMQ real
  - si Docker no está disponible, el test hace `skip` explícito con el motivo para mantener la suite determinística

## Docker local

Para demo y desarrollo local simple, el repo incluye un `docker-compose.yml` en la raíz que levanta:

- `customer-service`
- `rabbitmq`

### Levantar el stack

Desde la raíz del repo:

```bash
docker compose up --build -d
```

### Bajar el stack

```bash
docker compose down
```

Si además querés limpiar el volumen nombrado de RabbitMQ:

```bash
docker compose down -v
```

### Persistencia SQLite

- la base SQLite sigue viviendo en `services/customer-service/data/`
- compose monta `./services/customer-service/data:/app/data`
- el archivo esperado dentro del contenedor es `./data/customer-service.sqlite`

### Variables relevantes en compose

- `CUSTOMER_SERVICE_DATABASE_URL=sqlite:///./data/customer-service.sqlite`
- `CUSTOMER_SERVICE_EVENT_PUBLISHER_BACKEND=rabbitmq`
- `CUSTOMER_SERVICE_RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/%2F`
- `CUSTOMER_SERVICE_RABBITMQ_EXCHANGE=customer.events`

### Verificación rápida

- API health: `http://localhost:8000/health`
- RabbitMQ management: `http://localhost:15672` (`guest` / `guest`)

### Notas

- esta configuración está pensada para entorno local, demo y desarrollo, no para producción
- para pruebas administrativas locales puede ser necesario promover manualmente un usuario a rol `admin` en SQLite
