# 4.1. Booking Context

Contexto central del sistema. Gestiona el ciclo de vida completo de una reserva: creación, confirmación y cancelación. Orquesta la interacción con los demás contextos.

## Actores y Comandos

| Actor | Comando | Descripción |
|-------|---------|-------------|
| Cliente | CreateReservation | Solicita crear una nueva reserva para una habitación y rango de fechas |
| Cliente | CancelReservation | Solicita cancelar una reserva existente activa |
| Sistema (Payment) | ConfirmReservation | Confirma la reserva luego de que el pago fue aprobado |
| Sistema (Inventory) | RejectReservation | Rechaza la reserva si no hay disponibilidad en las fechas |

## Agregado (Aggregate Root)

### Reservation (Aggregate Root)

*Entidad central del contexto. Controla el ciclo de vida y garantiza la consistencia de la reserva.*

**Atributos:**

- `reservationId`: UUID — Identificador único
- `customerId`: UUID — Referencia al cliente (solo ID)
- `roomId`: UUID — Referencia a la habitación (solo ID)
- `dateRange`: DateRange — Período de la estadía
- `status`: ReservationStatus — Estado actual
- `totalPrice`: Money — Precio total calculado

**Estados:**

- Created → PendingPayment → Confirmed
- Created → Cancelled
- PendingPayment → Cancelled

## Value Objects

### DateRange

- `startDate`: LocalDate
- `endDate`: LocalDate

**Invariantes:**

- startDate debe ser anterior a endDate
- startDate no puede estar en el pasado
- Rango mínimo de 1 noche

### Money

- `amount`: Decimal
- `currency`: String (COP, USD)

**Invariantes:**

- amount debe ser mayor a cero
- currency no puede ser nulo

## Invariantes del Agregado

*Condiciones que el agregado debe garantizar en todo momento, independientemente de la operación:*

- Una Reservation no puede existir sin un DateRange válido (startDate < endDate, no en el pasado).
- Una Reservation no puede crearse sin customerId ni roomId referenciados.
- El totalPrice debe ser mayor a cero y calcularse antes de persistir la reserva.
- No es posible transicionar de Cancelled a ningún otro estado (estado terminal).
- No es posible transicionar a Confirmed sin haber pasado por PendingPayment (pago aprobado).
- No pueden existir dos Reservations con el mismo roomId con rangos de fechas solapados.

## Políticas

| Evento disparador | Política | Comando resultante |
|-------------------|----------|--------------------|
| PaymentApproved | Si el pago fue aprobado, confirmar la reserva automáticamente | ConfirmReservation |
| PaymentFailed | Si el pago falló, cancelar la reserva y liberar disponibilidad | CancelReservation |
| RoomAvailabilityBlocked | Si la disponibilidad fue bloqueada, pasar reserva a PendingPayment | RequestPayment |
| CustomerDeactivated | Si el cliente es desactivado, cancelar sus reservas pendientes | CancelReservation |

## Reglas de Negocio

1. No se puede crear una reserva con fechas inválidas o en el pasado.
2. Una reserva no puede crearse si la habitación no tiene disponibilidad en esas fechas.
3. Una reserva debe pasar por PendingPayment antes de ser Confirmed.
4. Una reserva Cancelled no puede ser Confirmed ni modificada.
5. El precio total se calcula como: PricePerNight × cantidad de noches.
6. Solo clientes activos y validados pueden crear reservas.

## Domain Events

| Evento | Cuándo se emite | Datos principales |
|--------|-----------------|-------------------|
| ReservationCreated | Al crear una reserva exitosamente | reservationId, customerId, roomId, dateRange, totalPrice |
| ReservationConfirmed | Al confirmar pago y disponibilidad | reservationId, confirmedAt |
| ReservationCancelled | Al cancelar una reserva | reservationId, cancelledAt, reason |
