# Declaración de uso de IA — Chilcon Ramirez Abondanyerri

## Sprint 1 (25–31 Mayo 2026)

### Boilerplate / scaffolding (declarado, sin tag en commits)

- **Configuración inicial del proyecto**: Docker, Django 5.x, PostgreSQL, settings con precisión decimal y logs JSON.
- Migraciones iniciales (generadas por Django + `makemigrations`, solo revisadas).

La política de evaluación lo permite explícitamente, y está declarado aquí sin necesidad de marcarlo en cada commit.

### Asistencia significativa [ai-assisted] (commits marcados)

- **Modelo User**: Implementación de `AbstractBaseUser` + `PermissionsMixin` con email como USERNAME_FIELD, validación de DNI peruano (módulo 11) y mayoría de edad.
- **Endpoints REST**: Register, Login (JWT), Me, Update Limits, Self-Exclusion.
- **Tests**: 51 tests con pytest, pytest-django, pytest-cov. Cobertura 99%.

### Lo que hice sin IA

- **Decisiones arquitectónicas**: estructura `apps/` vs flat, JWT vs Session.
- **Comprensión y verificación** del algoritmo de validación de DNI (módulo 11) — escribí y corregí el validador manualmente.
- **Análisis de trade-offs** en cada ADR — las opciones, contexto y consecuencias son mías; la IA solo ayudó a formatear el documento.
- **Ejecución y depuración** de tests fallidos (los 4 intentos fallidos documentados en lecciones.md).
- **Configuración del entorno Docker** y verificación manual de todos los endpoints con curl/Postman.
- **Documentación de proceso**: bitácora, lecciones.md y esta misma declaración — el contenido es mi experiencia, escrito por mí.

### Nota

Todo el código asistido fue revisado, modificado y comprendido antes de integrarse al repositorio. Puedo explicar y modificar cada línea en vivo, según lo requiere la política de evaluación del reto.
