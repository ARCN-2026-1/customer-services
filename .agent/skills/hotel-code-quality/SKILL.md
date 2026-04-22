---
name: hotel-code-quality
description: >
  Define reglas de calidad de código para este repositorio de forma agnóstica al
  lenguaje, incluyendo SOLID, Clean Code, DDD, refactor y comentarios. Trigger:
  cuando el agente vaya a escribir, revisar o refactorizar código.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

- Cuando se vaya a escribir código nuevo
- Cuando se revise calidad de implementación
- Cuando se haga refactor sin cambiar comportamiento observable
- Cuando se tomen decisiones sobre nombres, comentarios o estructura

## Critical Patterns

- Respetar bounded contexts y lenguaje ubicuo del dominio
- Aplicar **KISS**: preferir la solución más simple que resuelva el problema actual
- Aplicar **YAGNI**: no agregar capas, abstracciones o extensibilidad sin necesidad real
- Aplicar **DRY** con criterio: evitar duplicación significativa, no forzar reutilización prematura
- Mantener funciones y métodos con una responsabilidad principal
- Priorizar legibilidad antes que cleverness
- Hacer refactors pequeños y seguros

## Naming

- Los nombres deben expresar intención, no implementación accidental
- Usar términos del dominio cuando el código pertenezca a una capa de negocio
- Evitar nombres vagos como `data`, `value`, `manager`, `util`, `helper`, `temp`
- Variables: describir qué representan
- Funciones o métodos: describir qué hacen
- Clases o tipos: describir rol o concepto del dominio

## Ubiquitous Language

- En dominio y aplicación, usar el lenguaje del DDD definido para el proyecto
- Si el dominio habla de `Reservation`, `RoomAvailability` o `DateRange`, usar esos términos y no sinónimos arbitrarios
- No mezclar lenguaje técnico con lenguaje de negocio si eso degrada claridad
- Antes de nombrar entidades, value objects, eventos, comandos o estados, revisar la documentación en `docs/ddd/`
- El archivo de entrada para navegar el DDD es `docs/ddd/README.md`
- La definición de términos del dominio está en `docs/ddd/ubiquitous-language.md`
- Cada bounded context tiene su propio archivo en `docs/ddd/bounded-contexts/`

## SOLID Guidelines

### Single Responsibility Principle
- Cada módulo, clase o función debe tener una razón clara para cambiar

### Open/Closed Principle
- Extender comportamiento cuando haga falta, sin romper diseño existente innecesariamente

### Liskov Substitution Principle
- No introducir sustituciones que cambien expectativas o contratos

### Interface Segregation Principle
- Preferir interfaces pequeñas y enfocadas

### Dependency Inversion Principle
- El dominio no debe depender de detalles de infraestructura

## Clean Code Rules

- Reducir nesting innecesario
- Evitar funciones demasiado largas
- Evitar parámetros excesivos; agrupar cuando tenga sentido de dominio
- Manejar errores de forma explícita y coherente
- No esconder side effects
- No mezclar lógica de negocio con detalles de IO o framework

## Design Patterns

- Usar patrones solo cuando resuelvan una necesidad concreta
- Preferir composición antes que jerarquías complejas innecesarias
- En DDD, privilegiar entidades, value objects, servicios de dominio, repositorios y casos de uso antes que patrones ceremoniales
- No introducir factories, builders, strategies o decorators sin justificar la complejidad que agregan

## Refactoring

- Refactorizar para mejorar claridad, cohesión y aislamiento
- Mantener comportamiento observable intacto
- Evitar refactors masivos mezclados con features nuevas si pueden separarse
- Antes de abstraer, confirmar que la duplicación es real y estable

## Comments

- Los comentarios deben explicar **por qué**, no repetir **qué** hace el código
- Si un comentario explica una implementación confusa, primero intentar simplificar el código
- Documentar reglas de negocio no obvias, decisiones de diseño o restricciones externas
- Evitar comentarios obvios o desactualizables

## Warning Signs

- Clases o archivos con múltiples responsabilidades mezcladas
- Funciones con nombres ambiguos o genéricos
- Lógica de dominio puesta en `shared/`
- Comentarios que traducen línea por línea lo que ya se ve en el código
- Abstracciones creadas “por si acaso”
- Refactors grandes sin pruebas o sin separación clara del cambio funcional

## Decision Table

| Situación | Regla recomendada |
| --- | --- |
| Hay dos implementaciones parecidas pero todavía inestables | Duplicar temporalmente antes que abstraer mal |
| Una función hace validación, persistencia y mapeo | Separar por responsabilidad |
| El nombre no usa términos del dominio | Renombrar según lenguaje ubicuo |
| Un comentario explica cada línea | Borrar comentario y mejorar el código |
| Un patrón agrega más ruido que claridad | No usarlo |

## Code Examples

```text
Bueno: confirmReservation()
Malo: processReservationStuff()
```

```text
Bueno: DateRange, ReservationStatus, RoomAvailability
Malo: RangeData, StatusInfo, RoomManagerHelper
```

## Commands

```bash
git diff
git status
```

## Resources

- `README.md`
- `AGENTS.md`
- `.agent/skills/hotel-architecture-boundaries/SKILL.md`
- `docs/ddd/README.md`
- `docs/ddd/ubiquitous-language.md`
- `docs/ddd/bounded-contexts/`
