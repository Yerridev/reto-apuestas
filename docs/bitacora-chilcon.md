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
## Sprint 2 (28 Mayo 2026)

### Trabajado
- Servicio `withdraw()` con partida doble, validacion de saldo, cuenta verificada e idempotencia.
- Endpoint `POST /api/wallet/withdraw/` y tests de retiro.
- Validacion de monto maximo por apuesta y mensajes obligatorios de juego responsable.
- Servicio y endpoint de cashout con `Decimal`, `transaction.atomic()`, `select_for_update()` e idempotencia.
- Modelo `SuspiciousActivity`, reglas basicas antifraude, endpoint admin y dashboard operador.
- Frontend MVT con Django Templates y Tailwind CDN: home, login, registro, apuesta, wallet, historial, perfil y dashboard.
- ADRs de idempotencia, recotizacion de odds y frontend MVT.
- Documento de compliance simulado para Ley 31557 y DS 005-2023-MINCETUR.

### Bloqueantes
- Puerto local `5432` ocupado por otro contenedor PostgreSQL; se resolvio publicando la BD del proyecto en `5433`.

### Aprendizajes
1. `docker compose config` ayuda a comprobar si un override se esta aplicando realmente.
2. La idempotencia debe revisarse dentro de la transaccion para reducir riesgos de reintentos concurrentes.
