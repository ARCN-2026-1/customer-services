# 4.3. Customer Context

Gestiona el registro, validación y estado de los clientes del hotel. Otros contextos consultan este servicio para verificar que un cliente puede operar.

## Actores y Comandos

| Actor | Comando | Descripción |
|-------|---------|-------------|
| Cliente | RegisterCustomer | Se registra en el sistema con sus datos personales |
| Cliente | UpdateCustomerInfo | Actualiza su nombre, email u otros datos de contacto |
| Administrador | DeactivateCustomer | Desactiva la cuenta de un cliente por incumplimiento |
| Sistema (Booking) | CheckCustomerStatus | Consulta síncronamente si el cliente está activo (no es un comando, es una query que no cambia estado) |

## Agregado (Aggregate Root)

### Customer (Aggregate Root)

*Representa a un cliente registrado en el sistema con sus datos y estado.*

**Atributos:**

- `customerId`: UUID — Identificador único
- `name`: String — Nombre completo
- `email`: Email — Correo electrónico único
- `phone`: String — Teléfono de contacto
- `status`: CustomerStatus — Activo | Inactivo | Suspendido
- `registeredAt`: DateTime — Fecha de registro

**Estados:**

- Activo
- Inactivo
- Suspendido

## Value Objects

### Email

- `value`: String

**Invariantes:**

- Debe tener formato válido (contener @ y dominio)
- No puede estar vacío
- Debe ser único en el sistema

## Invariantes del Agregado

*Condiciones que el agregado debe garantizar en todo momento, independientemente de la operación:*

- No pueden existir dos Customer con el mismo valor de Email en el sistema.
- Un Customer con status Inactivo o Suspendido no puede generar comandos que modifiquen reservas.
- El nombre y email son obligatorios; un Customer no puede existir sin ellos.
- Solo se puede pasar a Inactivo desde Activo; un Customer Suspendido requiere resolución explícita.
- Solo se puede pasar a Suspendido desde Activo.

## Políticas

| Evento disparador | Política | Comando resultante |
|-------------------|----------|--------------------|
| CustomerDeactivated | Al desactivarse un cliente, notificar al Booking Context para cancelar reservas pendientes | CancelPendingReservations |
| CustomerRegistered | Al registrarse, el cliente queda automáticamente en estado Activo y puede reservar de inmediato. No se requiere activación manual. | — (sin comando adicional) |

## Reglas de Negocio

12. El email debe ser único en el sistema; no pueden existir dos clientes con el mismo email.
13. Un cliente inactivo o suspendido no puede crear nuevas reservas.
14. No se puede eliminar un cliente con reservas activas; solo desactivar.
15. La validación de cliente debe responder en tiempo real para no bloquear el flujo de reserva.

## Domain Events

| Evento | Cuándo se emite | Datos principales |
|--------|-----------------|-------------------|
| CustomerRegistered | Al registrar un cliente exitosamente | customerId, name, email, registeredAt |
| CustomerDeactivated | Al desactivar la cuenta de un cliente | customerId, deactivatedAt, reason |
| CustomerInfoUpdated | Al actualizar datos del cliente | customerId, updatedFields |
| CustomerSuspended | Al suspender temporalmente un cliente por incumplimiento | customerId, suspendedAt, reason |
