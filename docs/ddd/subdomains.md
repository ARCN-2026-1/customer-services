# 3. Subdominios

El dominio principal se divide según su criticidad para el negocio:

| Subdominio | Tipo | Microservicio | Descripción |
|------------|------|---------------|-------------|
| Gestión de Reservas | Core Domain | Booking Service | Núcleo del negocio. Controla el ciclo de vida de las reservas |
| Inventario de Habitaciones | Supporting Domain | Inventory Service | Administra habitaciones y valida disponibilidad en fechas |
| Gestión de Clientes | Supporting Domain | Customer Service | Gestiona información y validación de clientes |
| Procesamiento de Pagos | Generic Domain | Payment Service | Procesa transacciones económicas. Puede externalizarse |
