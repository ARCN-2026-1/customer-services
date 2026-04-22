# Flujo de trabajo en Git

## Objetivo

Definir una estrategia simple y ordenada de trabajo en Git para el proyecto de gestión de reservas de hotel, considerando un equipo de 4 integrantes y una arquitectura basada en microservicios.

## Estrategia elegida

Se usará un flujo basado en:

- `main`: rama estable y entregable
- `develop`: rama de integración del equipo
- ramas temporales por tarea

---

## Ramas principales

### `main`

- Contiene la versión estable del proyecto
- Solo debe recibir cambios aprobados y probados
- Representa el estado listo para entrega o demo

### `develop`

- Rama de integración del equipo
- Todas las features, fixes y cambios de documentación se integran primero acá
- Se usa como base para nuevas ramas de trabajo

---

## Ramas de trabajo

Cada tarea debe hacerse en una rama separada creada desde `develop`.

### Convenciones

- `feature/<servicio>-<descripcion>`
- `fix/<servicio>-<descripcion>`
- `docs/<descripcion>`
- `chore/<descripcion>`

### Ejemplos

- `feature/booking-create-reservation`
- `feature/inventory-search-rooms`
- `feature/customer-register-customer`
- `feature/payment-process-payment`
- `fix/booking-invalid-date-range`
- `docs/context-map`
- `chore/add-ci-pipeline`

---

## Flujo de trabajo del equipo

1. Actualizar la rama `develop`
2. Crear una rama nueva desde `develop`
3. Implementar una tarea concreta
4. Hacer commits pequeños y claros
5. Abrir Pull Request hacia `develop`
6. Revisar, probar e integrar
7. Pasar a `main` solo cuando `develop` esté estable

---

## Flujo paso a paso

### 1. Cambiar a `develop`

```bash
git checkout develop
```

### 2. Traer últimos cambios

```bash
git pull origin develop
```

### 3. Crear rama de trabajo

```bash
git checkout -b feature/booking-create-reservation
```

### 4. Trabajar y hacer commits

```bash
git add .
git commit -m "feat(booking): add create reservation use case"
```

### 5. Subir rama remota

```bash
git push -u origin feature/booking-create-reservation
```

### 6. Abrir Pull Request

El Pull Request debe apuntar a `develop`.

### 7. Merge a `main`

Cuando se cierre una iteración o entrega:

```bash
git checkout main
git pull origin main
git merge develop
git push origin main
```

---

## Reglas del equipo

### Reglas generales

- No trabajar directamente sobre `main`
- No trabajar directamente sobre `develop` para implementar features grandes
- Una rama debe representar una sola tarea o cambio concreto
- Todo cambio importante debe entrar por Pull Request
- Antes de mergear, el cambio debe estar revisado y probado

### Reglas de commits

- Usar Conventional Commits
- Hacer commits pequeños
- El mensaje debe describir intención, no cosas genéricas como `avance` o `cambios`

---

## Responsabilidades sugeridas por rol

### Backend Developer 1

- `booking-service`
- `customer-service`

### Backend Developer 2

- `inventory-service`
- `payment-service`

### QA / Testing Engineer

- pruebas unitarias
- pruebas de integración
- validación funcional
- revisión de criterios de aceptación

### DevOps / Integración

- CI/CD
- integración entre servicios
- Docker / despliegue local
- análisis estático y automatizaciones

---

## Recomendación para Pull Requests

Cada Pull Request debería incluir:

- objetivo del cambio
- servicio afectado
- evidencia de prueba
- riesgos o consideraciones

### Plantilla sugerida

```md
## Objetivo

## Servicio afectado

## Qué se hizo

## Cómo se probó

## Observaciones
```

---

## Criterio para pasar de `develop` a `main`

Se puede promover a `main` cuando:

- los cambios principales están integrados
- no hay errores críticos conocidos
- las pruebas acordadas pasan
- el equipo valida que la versión está lista para entrega

---

## Resumen

El proyecto va a usar un flujo simple:

- `main` como rama estable
- `develop` como rama de integración
- ramas temporales por tarea
- Pull Requests hacia `develop`
- promoción controlada de `develop` a `main`

Este flujo reduce el caos, facilita el trabajo en paralelo y es suficiente para el tamaño actual del equipo.
