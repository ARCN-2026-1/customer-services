# 4.4. Payment Context

Gestiona el procesamiento de pagos y reembolsos asociados a las reservas. Es un dominio genérico que podría integrarse con pasarelas externas como Stripe o PayU.

## Actores y Comandos

| Actor | Comando | Descripción |
|-------|---------|-------------|
| Sistema (Booking) | ProcessPayment | Inicia el cobro del total al crearse la reserva, antes de que sea confirmada |
| Cliente | RequestRefund | Solicita el reembolso al cancelar una reserva confirmada |
| Sistema | RetryPayment | Reintenta el cobro si el primer intento falla por error transitorio |

## Agregado (Aggregate Root)

### Payment (Aggregate Root)

*Representa una transacción de pago asociada a una reserva. Controla el estado del cobro.*

**Atributos:**

- `paymentId`: UUID — Identificador único
- `reservationId`: UUID — Reserva asociada
- `customerId`: UUID — Cliente que realiza el pago
- `amount`: Money — Monto total cobrado
- `method`: PaymentMethod — Tarjeta | Transferencia | PSE
- `status`: PaymentStatus — Pendiente | Aprobado | Rechazado | Reembolsado
- `processedAt`: DateTime — Fecha de procesamiento
- `gatewayReference`: String — Código de referencia externo

**Estados:**

- Pendiente → Aprobado
- Pendiente → Rechazado
- Aprobado → Reembolsado

## Value Objects

### Money

- `amount`: Decimal
- `currency`: String (COP, USD)

**Invariantes:**

- amount debe ser mayor a cero
- Debe coincidir con el totalPrice de la Reservation asociada

## Invariantes del Agregado

*Condiciones que el agregado debe garantizar en todo momento, independientemente de la operación:*

- El amount del Payment debe coincidir exactamente con el totalPrice de la Reservation asociada.
- No se puede emitir un reembolso sobre un Payment que no esté en estado Aprobado.
- Un Payment en estado Rechazado puede reintentarse máximo 2 veces; al tercer rechazo se cancela la reserva.
- No pueden existir dos Payment activos para la misma reservationId simultáneamente.
- El gatewayReference debe quedar registrado antes de marcar un Payment como Aprobado.

## Políticas

| Evento disparador | Política | Comando resultante |
|-------------------|----------|--------------------|
| ReservationCreated | Al crearse una reserva, iniciar el proceso de cobro automáticamente | ProcessPayment |
| PaymentFailed | Si el pago falla, emitir PaymentFailed para que Booking Context cancele la reserva automáticamente | CancelReservation (en Booking) |
| ReservationCancelled | Si la reserva cancelada fue Confirmed, iniciar reembolso automático | RequestRefund |

## Reglas de Negocio

16. El monto del pago debe coincidir exactamente con el totalPrice de la reserva.
17. Un pago rechazado puede reintentarse máximo 2 veces antes de cancelar la reserva.
18. Solo se puede reembolsar un pago con status Aprobado.
19. El reembolso aplica solo si la cancelación se realiza con más de 24 horas de antelación.
20. El sistema debe guardar la referencia externa de la pasarela de pago para trazabilidad.

## Domain Events

| Evento | Cuándo se emite | Datos principales |
|--------|-----------------|-------------------|
| PaymentInitiated | Al iniciar el proceso de cobro | paymentId, reservationId, amount |
| PaymentApproved | Al aprobar el pago exitosamente | paymentId, reservationId, approvedAt, gatewayRef |
| PaymentFailed | Al rechazarse el pago | paymentId, reservationId, reason, attempt |
| PaymentRefunded | Al procesar un reembolso | paymentId, reservationId, refundedAt, amount |
