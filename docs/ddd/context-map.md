# 5. Context Map

Describe cómo se relacionan los Bounded Contexts entre sí y el tipo de integración utilizado.

| Upstream (proveedor) | Downstream (consumidor) | Tipo de relación | Integración |
|----------------------|-------------------------|------------------|-------------|
| Inventory Context | Booking Context | Customer / Supplier | Síncrona — Booking consulta disponibilidad antes de crear la reserva |
| Customer Context | Booking Context | Customer / Supplier | Síncrona — Booking valida que el cliente exista y esté activo |
| Booking Context | Payment Context | Customer / Supplier | Asíncrona — Booking emite ReservationCreated para iniciar el cobro |
| Booking Context | Inventory Context | Published Language | Asíncrona — Booking emite ReservationCancelled para liberar disponibilidad |
| Payment Context | Booking Context | Published Language | Asíncrona — Payment emite PaymentApproved/Failed para confirmar o cancelar |
| Customer Context | Booking Context | Published Language | Asíncrona — Customer emite CustomerDeactivated para cancelar reservas |

## Tipos de comunicación usados

- **Síncrona (REST/gRPC):** validaciones en tiempo real antes de crear la reserva
- **Asíncrona (mensajería/eventos):** acciones que ocurren después de un hecho del dominio
