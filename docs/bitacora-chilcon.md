# Bitácora — Chilcon Ramirez Abondanyerri

## Sprint 1 (25–31 Mayo 2026)

### Trabajado
- Configuración del proyecto: Docker + Django 5.x + PostgreSQL + DRF.
- Estructura base: apps/ con wallet, betting, users, audit + docs/ con adr/ y sketches/.
- Modelo User custom (AbstractBaseUser + PermissionsMixin) con:
  - Login por email.
  - Validación de DNI peruano (módulo 11, 8 dígitos + DV).
  - Validación de mayoría de edad (≥ 18).
  - Estados de cuenta: pendiente_verificacion, verificado, bloqueado, autoexcluido.
  - Límites de depósito configurables (diario, semanal, mensual) con cooldown 24h.
  - Autoexclusión temporal (7/30/90 días) e indefinida.
- Endpoints REST: register, login (JWT), me, update limits, self-exclusion.
- 51 tests con pytest, 99% de cobertura en apps/users.
- ADR-0001 (estructura y precisión), ADR-0002 (autenticación JWT), ADR-0008 (juego responsable).
- Documentación de proceso.

### Bloqueantes
- Ninguno hasta ahora. El entorno Docker funciona correctamente.

### Aprendizajes
1. Los validators de campo en Django no se ejecutan en `save()`, solo en `full_clean()`. El UserManager debe llamar `user.full_clean()` explícitamente.
2. DRF sobreescribe los validators del modelo si se pasan por `extra_kwargs` con clave `validators`. La forma correcta es usar métodos `validate_<campo>()` en el serializer.
3. El throttle rate de DRF se aplica también a tests. Si un test falla y reintenta, puede agotar el rate limit y causar falsos 429.
4. La variable `DJANGO_SETTINGS_MODULE` debe estar seteada antes de importar cualquier módulo de Django; de lo contrario, las importaciones fallan silenciosamente.
