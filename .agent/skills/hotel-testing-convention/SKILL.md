---
name: hotel-testing-convention
description: >
  Define reglas de testing para este repositorio de forma agnóstica al lenguaje,
  incluyendo estructura AAA, naming consistente, cobertura y buenas prácticas de
  aislamiento. Trigger: cuando el agente vaya a escribir, revisar o proponer tests.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

- Cuando se escriban tests unitarios, de integración o de contrato
- Cuando se revise la calidad de una suite de pruebas
- Cuando se agregue o configure coverage para CI y SonarCloud

## Critical Patterns

- Cada test debe seguir la estructura **AAA**: Arrange, Act, Assert
- El test debe verificar una sola conducta principal
- El nombre del test debe describir claramente el escenario y el resultado esperado
- Evitar lógica compleja dentro del test; si el test parece una mini aplicación, está mal diseñado
- Usar datos mínimos y explícitos para que el motivo del test sea obvio
- Priorizar tests determinísticos: sin dependencia de hora real, red real ni estado global mutable

## Naming Convention

Usar el patrón:

`When_[StateUnderTest]_Expect_[ExpectedBehavior]`

Ejemplos:

```text
When_DateRangeIsInvalid_Expect_ReservationCreationToFail
When_PaymentIsApproved_Expect_ReservationToBeConfirmed
When_RoomIsAlreadyBlocked_Expect_AvailabilityRequestToBeRejected
```

Si el lenguaje o framework ya impone una convención distinta, mantener la intención del patrón aunque cambie el formato.

## AAA Structure

Todo test debe quedar organizado en tres partes claras:

1. **Arrange**: preparar el estado, fixtures, mocks y entradas
2. **Act**: ejecutar la operación bajo prueba
3. **Assert**: verificar el resultado esperado

## Test Design Rules

- Un test debe fallar por una sola razón
- No mezclar múltiples escenarios en el mismo test
- No repetir asserts redundantes si no agregan valor
- Testear comportamiento observable, no detalles internos innecesarios
- Preferir builders, factories o helpers cuando el setup empiece a repetirse
- Si una dependencia externa es irrelevante para el objetivo del test, reemplazarla por un doble de prueba

## Types of Tests

### Unit tests

- Aislados
- Rápidos
- Sin acceso real a red, filesystem o base de datos, salvo que eso sea exactamente lo que se esté probando

### Integration tests

- Validan interacción entre módulos o adaptadores reales
- Deben ser menos numerosos que los unit tests
- Usar datos controlados y limpiar el estado al finalizar

### Contract tests

- Validan payloads, esquemas y compatibilidad entre servicios
- Son especialmente importantes para eventos y APIs compartidas

## Coverage

- El objetivo de coverage en este repo es **70% mínimo sobre código nuevo** cuando el pipeline de tests esté activo
- Coverage no reemplaza criterio: un porcentaje alto con tests pobres sigue siendo mala calidad
- La cobertura debe enviarse a SonarCloud a través de reportes generados por CI
- No manipular tests solo para inflar el porcentaje

## Good Practices

- Incluir casos felices y casos de error relevantes
- Cubrir reglas de negocio, invariantes y bordes importantes
- Probar mensajes de error o códigos de fallo cuando formen parte del contrato
- Evitar sleeps, temporizadores reales y dependencias de orden entre tests
- Mantener los tests cerca del módulo o capa que validan, según la convención del servicio

## Warning Signs

- Tests con nombres vagos como `test_1`, `should_work`, `happy_path`
- Tests que dependen de ejecución previa de otros tests
- Assertions demasiado amplias o poco específicas
- Setup enorme para validar una conducta mínima
- Mocks en exceso que terminan replicando la implementación real

## Code Examples

```text
Arrange: crear reservation válida con fechas futuras
Act: ejecutar create reservation
Assert: verificar que queda en estado Created
```

```text
When_CustomerIsInactive_Expect_ReservationCreationToFail
```

## Commands

```bash
git diff
git status
```

## Resources

- `docs/sonarcloud.md`
- `AGENTS.md`
