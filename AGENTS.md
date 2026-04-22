# AGENTS.md

## Propósito

Este archivo define las reglas base para agentes que trabajen en este repositorio. Su objetivo es mantener consistencia en commits, Pull Requests y límites arquitectónicos entre microservicios.

## Reglas del proyecto

- Respetar la estructura de monorepo y los bounded contexts definidos.
- No mover lógica de dominio a `shared/`.
- Usar Conventional Commits con scope por servicio o módulo.
- Todo Pull Request debe apuntar a `develop` salvo una instrucción explícita distinta.
- Todo Pull Request debe usar la plantilla ubicada en `.github/pull_request_template.md`.
- Los cambios deben ser pequeños, revisables y enfocados en una sola intención.

## Flujo esperado

1. Leer el contexto necesario.
2. Aplicar la skill correspondiente según el tipo de trabajo.
3. Hacer cambios mínimos y consistentes con la arquitectura.
4. Documentar o proponer el commit con el formato correcto.
5. Preparar PR hacia `develop` usando la plantilla del repo.

## Skills disponibles

| Skill | Uso | Ubicación |
| --- | --- | --- |
| `hotel-git-commit` | Convención de commits y scopes válidos | `.agent/skills/hotel-git-commit/SKILL.md` |
| `hotel-pr-convention` | Reglas para Pull Requests y uso de template | `.agent/skills/hotel-pr-convention/SKILL.md` |
| `hotel-testing-convention` | Reglas de testing, naming, AAA y coverage | `.agent/skills/hotel-testing-convention/SKILL.md` |
| `hotel-code-quality` | Reglas de calidad de código, DDD, Clean Code y refactor | `.agent/skills/hotel-code-quality/SKILL.md` |

## Cuándo usar cada skill

- Si el trabajo implica preparar o sugerir un commit, cargar `hotel-git-commit`.
- Si el trabajo implica abrir, revisar o preparar un PR, cargar `hotel-pr-convention`.
- Si el trabajo implica crear o mover código entre servicios, cargar `hotel-architecture-boundaries`.
- Si el trabajo implica escribir, revisar o mejorar tests, cargar `hotel-testing-convention`.
- Si el trabajo implica escribir, revisar o refactorizar código, cargar `hotel-code-quality`.
- Si aplican varias, cargar todas.

## Prioridades

En caso de conflicto, priorizar:

1. límites arquitectónicos
2. calidad de código
3. convención de testing
4. convención de PR
5. convención de commits


## Referencias del repo

- `README.md`
- `docs/git-workflow.md`
- `.github/pull_request_template.md`
