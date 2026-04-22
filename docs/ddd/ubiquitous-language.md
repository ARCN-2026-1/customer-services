# 2. Lenguaje Ubicuo

Términos clave usados de forma consistente en todos los contextos del sistema:

| Término | Definición |
|---------|------------|
| Reserva (Reservation) | Solicitud formal de ocupación de una habitación en un rango de fechas |
| Habitación (Room) | Unidad física del hotel con tipo, capacidad y precio por noche |
| Cliente (Customer) | Persona registrada que puede realizar y gestionar reservas |
| Disponibilidad (Availability) | Estado que indica si una habitación puede ser reservada en unas fechas |
| Rango de Fechas (DateRange) | Período con fecha de inicio y fin que define la estadía |
| Confirmación (Confirmation) | Estado que indica que la reserva fue validada y el pago procesado |
| Cancelación (Cancellation) | Acción que termina una reserva activa |
| Precio por Noche (PricePerNight) | Valor monetario cobrado por la ocupación de una habitación por noche |
| Tipo de Habitación (RoomType) | Categoría: Simple, Doble, Suite, Familiar |
| Pago (Payment) | Transacción económica asociada al costo total de una reserva |
| Filtro de Búsqueda (RoomFilter) | Criterios para buscar habitaciones: tipo, precio máximo, fechas |
| Actor | Persona o sistema que desencadena una acción dentro del dominio |
| Comando (Command) | Intención de realizar una acción que puede cambiar el estado del sistema |
| Política (Policy) | Regla que reacciona a un evento y dispara un nuevo comando automáticamente |
| Evento de Dominio (Domain Event) | Hecho relevante del negocio que ya ocurrió dentro del dominio |
