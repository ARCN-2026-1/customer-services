# Services Docs

## Propósito

Esta carpeta centraliza la documentación funcional y de integración de los microservicios del sistema.

## Regla del proyecto

Cada vez que se cree o evolucione un microservicio, se deben actualizar dos cosas:

1. su documento propio en `docs/services/<service-name>.md`
2. el mapa de integración en `docs/services/integration-map.md`

La idea es que el equipo pueda responder rápido estas preguntas:

- qué hace cada servicio
- de quién depende para operar
- qué endpoints expone a otros servicios
- qué eventos publica
- qué endpoints o eventos consume

## Documentos actuales

- `customer-service.md` — contrato funcional y técnico del servicio de clientes
- `inventory-service.md` — definición funcional inicial del servicio de disponibilidad
- `integration-map.md` — mapa central de integraciones entre servicios
