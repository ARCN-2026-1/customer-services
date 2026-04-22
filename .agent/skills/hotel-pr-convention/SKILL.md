---
name: hotel-pr-convention
description: >
  Define cómo preparar Pull Requests en este repositorio, a qué rama apuntan
  y cómo usar la plantilla del proyecto. Trigger: cuando el agente vaya a crear,
  preparar o revisar un Pull Request.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

- Cuando se vaya a abrir un Pull Request
- Cuando se redacte el contenido de un PR
- Cuando se revise si un PR cumple las reglas del equipo

## Critical Patterns

- El PR debe apuntar a `develop`
- Debe usarse la plantilla `.github/pull_request_template.md`
- El contenido debe ser concreto: objetivo, servicio afectado, pruebas y observaciones
- El PR debe representar un cambio acotado y revisable

## Review Checklist

- La rama sale de `develop`
- El cambio tiene una sola intención principal
- El servicio afectado está claro
- Se documentó cómo se probó
- No se mezclan cambios de dominio con cambios no relacionados

## Code Examples

```text
Base branch: develop
Template: .github/pull_request_template.md
```

## Commands

```bash
git status
git log --oneline -5
gh pr create --base develop
```

## Resources

- `.github/pull_request_template.md`
- `docs/git-workflow.md`
- `AGENTS.md`
