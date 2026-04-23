# Customer Context

Gestiona el alta, autenticación básica del MVP, datos de contacto y estado operativo de los clientes. Otros contextos consultan este servicio para obtener datos del cliente y validar si puede participar en el flujo de reservas.

## Actores y comandos / casos de uso

| Actor | Comando / caso de uso | Descripción |
|-------|------------------------|-------------|
| Cliente | `RegisterCustomer` | Se registra con nombre, email, teléfono opcional y contraseña |
| Cliente | `AuthenticateCustomer` | Inicia sesión con email y contraseña para obtener un JWT |
| Administrador | `UpdateCustomerInfo` | Actualiza nombre o teléfono de un cliente |
| Administrador | `DeactivateCustomer` | Pasa un cliente `ACTIVE` a `INACTIVE` |
| Administrador | `ActivateCustomer` | Reactiva un cliente `INACTIVE` |
| Administrador | `SuspendCustomer` | Pasa un cliente `ACTIVE` a `SUSPENDED` |
| Administrador | `ResolveCustomerSuspension` | Devuelve un cliente `SUSPENDED` a `ACTIVE` |
| Administrador | `ListCustomers` | Lista los clientes registrados |
| Sistema (Booking / integraciones internas) | `GetCustomerById` | Consulta datos básicos del cliente |
| Sistema (Booking / integraciones internas) | `ValidateCustomerForReservation` | Verifica si el cliente está habilitado para reservar |
| Sistema (mensajería) | `BookingCreated` → validación asíncrona | Consume el evento entrante y publica `CustomerValidationResult` |

## Aggregate Root

### Customer

- `customerId`: UUID
- `name`: String
- `email`: Email
- `phone`: String?
- `passwordHash`: String
- `status`: `CustomerStatus` (`ACTIVE`, `INACTIVE`, `SUSPENDED`)
- `role`: `CustomerRole` (`customer`, `admin`)
- `registeredAt`: DateTime

El aggregate unifica identidad autenticable y perfil de cliente como decisión explícita del MVP.

## Invariantes

- No pueden existir dos `Customer` con el mismo `Email`.
- El nombre es obligatorio.
- `passwordHash` es obligatorio y nunca se expone por la API.
- Un `Customer` solo es elegible para reservar cuando está en estado `ACTIVE`.
- Solo se puede pasar a `INACTIVE` desde `ACTIVE`.
- Solo se puede pasar a `SUSPENDED` desde `ACTIVE`.
- Solo se puede pasar a `ACTIVE` desde `INACTIVE` o resolver una suspensión desde `SUSPENDED`, según el caso de uso.
- Un cliente `SUSPENDED` no puede ser desactivado directamente.

## Domain Events implementados

- `CustomerRegistered`
- `CustomerInfoUpdated`
- `CustomerDeactivated`
- `CustomerActivated`
- `CustomerSuspended`
- `CustomerSuspensionResolved`
- `CustomerValidationResult` *(evento de integración saliente derivado de la validación asíncrona de reservas)*

## Políticas relevantes

- al registrarse, el cliente queda `ACTIVE` automáticamente en el MVP
- los endpoints administrativos requieren autenticación Bearer con rol `admin`
- Booking puede consultar elegibilidad en tiempo real por REST o disparar validación asíncrona vía `BookingCreated`
- la respuesta asíncrona devuelve solo campos de correlación (`bookingId`, `customerId`) y `isValid`
