# 4.2. Inventory Context

Administra el catálogo de habitaciones del hotel y controla la disponibilidad. Responde a consultas de búsqueda y bloquea/libera períodos de ocupación.

## Actores y Comandos

| Actor | Comando | Descripción |
|-------|---------|-------------|
| Cliente | SearchRooms | Busca habitaciones disponibles filtrando por fechas, tipo y precio |
| Administrador | RegisterRoom | Registra una nueva habitación en el sistema |
| Administrador | UpdateRoomStatus | Cambia el estado de una habitación (mantenimiento, disponible) |
| Sistema (Booking) | BlockRoomAvailability | Bloquea fechas de una habitación al crear una reserva |
| Sistema (Booking) | ReleaseRoomAvailability | Libera fechas al cancelarse una reserva |

## Agregado (Aggregate Root)

### Room (Aggregate Root)

*Representa una habitación física del hotel. Contiene la disponibilidad como parte del agregado.*

**Atributos:**

- `roomId`: UUID — Identificador único
- `roomNumber`: String — Número físico de la habitación
- `roomType`: RoomType — Simple | Doble | Suite | Familiar
- `capacity`: Integer — Número máximo de huéspedes
- `pricePerNight`: Money — Precio base por noche
- `operationalStatus`: RoomOperationalStatus — Operativa | EnMantenimiento | Inactiva
- `availabilityPeriods`: List\<RoomAvailability\> — Períodos bloqueados por reservas activas (consistencia del agregado; en producción puede externalizarse)

## Entidades

### RoomAvailability

*Registra un período en que la habitación está bloqueada por una reserva.*

**Atributos:**

- `availabilityId`: UUID
- `roomId`: UUID — Habitación a la que pertenece
- `reservationId`: UUID — Reserva que ocupa el período
- `dateRange`: DateRange — Período bloqueado

## Value Objects

### RoomFilter

- `dateRange`: DateRange — Fechas deseadas (obligatorio)
- `roomType`: RoomType (opcional) — Filtro por tipo
- `maxPrice`: Money (opcional) — Precio máximo por noche
- `minCapacity`: Integer (opcional) — Capacidad mínima requerida

## Invariantes del Agregado

*Condiciones que el agregado debe garantizar en todo momento, independientemente de la operación:*

- Una Room no puede tener dos RoomAvailability con rangos de fechas solapados.
- Solo una Room con operationalStatus Operativa puede aceptar nuevos bloqueos de disponibilidad.
- Liberar una disponibilidad (RoomAvailabilityReleased) no modifica el operationalStatus de la habitación.
- El pricePerNight debe ser mayor a cero en toda Room registrada.
- Una Room en estado Inactiva no puede tener nuevos períodos de disponibilidad creados.

## Políticas

| Evento disparador | Política | Comando resultante |
|-------------------|----------|--------------------|
| ReservationCancelled | Al cancelarse una reserva, liberar automáticamente las fechas bloqueadas | ReleaseRoomAvailability |
| ReservationCreated | Al crearse una reserva, intentar bloquear las fechas de la habitación | BlockRoomAvailability |

## Reglas de Negocio

7. Una habitación no puede tener dos reservas con rangos de fechas solapados.
8. Solo habitaciones con operationalStatus Operativa aparecen en resultados de búsqueda.
9. El filtro por precio compara contra pricePerNight de cada habitación.
10. Una habitación en mantenimiento no puede ser reservada.
11. Al liberarse una reserva, solo se elimina el período bloqueado. El estado operativo de la habitación no cambia automáticamente; puede seguir en mantenimiento o inactiva.

## Domain Events

| Evento | Cuándo se emite | Datos principales |
|--------|-----------------|-------------------|
| RoomAvailabilityBlocked | Al bloquear fechas de una habitación para una reserva | roomId, reservationId, dateRange |
| RoomAvailabilityReleased | Al liberar fechas al cancelarse una reserva. El estado operativo de la habitación no cambia automáticamente. | roomId, reservationId, dateRange |
| RoomRegistered | Al registrar una nueva habitación en el sistema | roomId, roomType, pricePerNight |
| RoomStatusChanged | Al cambiar el estado operativo (ej: pasa a EnMantenimiento o vuelve a Operativa) | roomId, previousStatus, newStatus |
