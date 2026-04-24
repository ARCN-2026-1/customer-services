# Customer Service Overview

## Propósito

Gestionar clientes y su estado dentro del sistema. En el MVP actual, este servicio también resuelve la autenticación básica del usuario, por lo que `Customer` representa tanto al cliente del negocio como al usuario autenticable del sistema.

> Este documento existe para dar contexto rápido. Para detalle operativo, endpoints, eventos y diagramas del runtime, ver `docs/services/customer-service.md`.

## Responsabilidades principales

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
- implementar refresh tokens o revocación compleja

## Entradas y salidas de integración

- síncrona: `GET /customers/{customerId}` y `GET /customers/{customerId}/reservation-eligibility`
- asíncrona saliente: eventos de ciclo de vida del cliente
- asíncrona entrante: consumo de `BookingCreated` para responder con `CustomerValidationResult`

## Estados del cliente

- `ACTIVE`
- `INACTIVE`
- `SUSPENDED`

## Reglas relevantes

- el email debe ser único en el sistema
- el nombre y email son obligatorios
- `passwordHash` nunca debe exponerse por la API
- un cliente `INACTIVE` o `SUSPENDED` no puede crear nuevas reservas
- `DeactivateCustomer` solo aplica desde `ACTIVE`
- `ActivateCustomer` solo aplica desde `INACTIVE`
- `SuspendCustomer` solo aplica desde `ACTIVE`
- `ResolveCustomerSuspension` solo aplica desde `SUSPENDED`

## Integración

- síncrona: consulta de datos y elegibilidad vía REST
- asíncrona: consumo y publicación de eventos mediante RabbitMQ

## Validación técnica

```bash
uv run pytest
uv run pyright
uv run black --check .
uv run ruff check .
./scripts/validate.sh
```
