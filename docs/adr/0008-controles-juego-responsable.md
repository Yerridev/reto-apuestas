# ADR-0008: Controles de juego responsable

**Fecha:** 2026-05-25 | **Autor:** Chilcon Ramirez Abondanyerri (Grupo 06)

## Contexto
El RETO exige implementar controles de juego responsable como requisito funcional obligatorio del Núcleo (Nivel 1). Requisitos: límites de depósito configurables con cooldown de 24h al subir, autoexclusión temporal (7/30/90 días) o indefinida no reversible antes del plazo, y mensaje de consumo responsable en pantallas.

## Opciones consideradas

| Decisión | Opción A | Opción B | Elegida |
|---|---|---|---|
| Límites de depósito | Fijos por el admin (config en settings) | Configurables por usuario con cooldown | **B** — requisito del RETO, da agencia al usuario |
| Modelo de autoexclusión | Booleano en User + fecha hardcodeada | Tabla `SelfExclusion` con historial + tipos | **B** — auditable, trazable, permite consultar exclusiones pasadas |
| Control de cambios de límites | Solo campo `updated_at` en User | Tabla `DepositLimitChange` separada | **B** — cumple con requerimiento de auditoría |
| Cooldown al subir límites | 24h fijo | Configurable por tipo de límite | **A** — 24h fijo, requisito explícito del RETO |

## Decisión
1. Tres campos `Decimal` en `User`: `deposit_limit_daily`, `deposit_limit_weekly`, `deposit_limit_monthly`.
2. Cooldown de 24h al subir cualquier límite; bajar es instantáneo.
3. Tabla `SelfExclusion` con `exclusion_type`, `start_date`, `end_date` (null = indefinida).
4. Tabla `DepositLimitChange` para auditoría de cada modificación de límite.
5. Mensaje de consumo responsable se implementará en el frontend (footer/base template) cuando se desarrolle.

## Consecuencias
- [+] Límites auditables y trazables (DepositLimitChange guarda old/new value).
- [+] Autoexclusión no puede revertirse antes del plazo — `end_date` se calcula al crear y no se modifica.
- [+] Cooldown de 24h bloquea subidas impulsivas; bajadas son inmediatas para proteger al usuario.
- [-] El mensaje de consumo responsable queda pendiente del frontend.
- [-] Sin notificaciones al usuario cuando el cooldown expira (podría agregarse con Celery+email en el futuro).
