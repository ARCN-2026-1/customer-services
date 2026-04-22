# SonarCloud

## Qué hace

Análisis estático de código que corre automáticamente en:

- cada PR hacia `develop`
- cada push a `develop`
- cada push a `main`

## Archivos involucrados

- `sonar-project.properties` — configuración del proyecto (organización, fuentes, exclusiones, patrones de test)
- `.github/workflows/sonar.yml` — workflow que dispara el análisis

## Requisitos

El secret `SONAR_TOKEN` debe estar configurado en GitHub.

## Métricas objetivo

- Bugs: 0
- Vulnerabilidades: 0
- Cobertura mínima: 70% sobre código nuevo (cuando haya tests y reportes de coverage)

## Protección de ramas

Después de que el workflow haya corrido al menos una vez, configurar en GitHub para `develop` y `main`:

- Require a pull request before merging
- Require status checks to pass before merging
- Seleccionar el check de SonarCloud como obligatorio

## Coverage

SonarCloud no genera cobertura — solo consume reportes que produce el pipeline de tests.

El camino para activarla:

1. Crear pipeline de tests por servicio
2. Generar reportes de cobertura en CI
3. Apuntar `sonar-project.properties` al reporte generado
4. Exigir cobertura mínima en el Quality Gate
