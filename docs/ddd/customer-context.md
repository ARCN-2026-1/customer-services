# Customer Context

Gestiona el registro, validación y estado de los clientes del hotel. Otros contextos consultan este servicio para verificar que un cliente puede operar.

## Actores y Comandos

| Actor | Comando | Descripción |
|-------|---------|-------------|
| Cliente | RegisterCustomer | Se registra en el sistema con sus datos personales |
| Cliente | UpdateCustomerInfo | Actualiza su nombre, email u otros datos de contacto |
| Administrador | DeactivateCustomer | Desactiva la cuenta de un cliente por incumplimiento |
| Sistema (Booking) | CheckCustomerStatus | Consulta síncronamente si el cliente está activo |

## Aggregate Root

### Customer

- `customerId`: UUID
- `name`: String
- `email`: Email
- `phone`: String
- `status`: CustomerStatus
- `registeredAt`: DateTime

## Invariantes

- No pueden existir dos `Customer` con el mismo `Email`.
- Un `Customer` inactivo o suspendido no puede crear reservas.
- El nombre y email son obligatorios.
- Solo se puede pasar a `INACTIVE` desde `ACTIVE`.
- Solo se puede pasar a `SUSPENDED` desde `ACTIVE`.

## Domain Events

- `CustomerRegistered`
- `CustomerDeactivated`
- `CustomerInfoUpdated`
- `CustomerSuspended`

## Políticas relevantes

- al desactivarse un cliente, Booking puede cancelar reservas pendientes
- al registrarse, el cliente queda activo automáticamente en el MVP
