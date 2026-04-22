---
name: hotel-git-commit
description: >
  Define cómo escribir commits en este repositorio usando Conventional Commits,
  scopes por servicio y mensajes claros. Trigger: cuando el agente vaya a crear,
  sugerir o revisar commits.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

- Cuando se vaya a proponer un mensaje de commit
- Cuando se vaya a crear un commit
- Cuando se revise si el historial está siguiendo la convención del proyecto

## Critical Patterns

- Usar formato `tipo(scope): mensaje`
- El mensaje debe describir intención, no una lista vaga de cambios
- Hacer commits pequeños y atómicos
- No usar mensajes como `avance`, `cambios`, `fix`, `update` sin contexto

## Allowed Types

- `feat`
- `fix`
- `docs`
- `test`
- `refactor`
- `chore`
- `ci`

## Allowed Scopes

- `booking`
- `inventory`
- `customer`
- `payment`
- `docs`
- `shared`
- `deploy`
- `repo`
- `ci`

## Code Examples

```text
feat(booking): add create reservation use case
fix(inventory): prevent overlapping availability periods
docs(repo): document git workflow and pr process
chore(repo): initialize repository foundations
```

## Commands

```bash
git status
git diff --staged
git commit -m "feat(booking): add create reservation use case"
```

## Resources

- `docs/git-workflow.md`
- `AGENTS.md`
