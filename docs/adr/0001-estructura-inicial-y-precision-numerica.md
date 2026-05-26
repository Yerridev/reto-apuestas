# ADR-0001: Estructura inicial y precisión numérica

**Fecha:** 2026-05-25 | **Autor:** Chilcon Ramirez Abodanyerri (Grupo 06)

## Contexto
Definir las bases arquitectónicas del proyecto antes de escribir lógica de negocio: layout de apps, precisión monetaria, motor BD y formato de logs.

## Opciones consideradas

| Decisión | Opción A | Opción B | Elegida |
|---|---|---|---|
| Layout apps | Plana (`/wallet/`, etc.) | Subpackage (`apps/wallet/`) | **B** — separación limpia, escala mejor |
| Precisión montos | `float` | `Decimal(18,4)` | **B** — exactitud financiera, requisito del reto |
| Motor BD | SQLite | PostgreSQL 16 | **B** — `select_for_update`, `NUMERIC`, concurrencia |
| Formato logs | Texto plano | JSON estructurado | **B** — parseable, integrable con observabilidad |

## Decisión
1. Apps bajo `apps/{wallet,betting,users,audit}`.
2. `Decimal(max_digits=18, decimal_places=4)` en todo monto; constantes `DECIMAL_MAX_DIGITS` / `DECIMAL_PLACES` en `settings.py`.
3. PostgreSQL 16 vía Docker.
4. Logging JSON con formatter custom (`config.logging_fmt.JSONFormatter`).

## Consecuencias
- [+] Apps aisladas del core de configuración; `NUMERIC(18,4)` elimina errores de redondeo; logging JSON facilitá trazabilidad de auditoría.
- [-] Importaciones con prefijo `apps.`; todo `DecimalField` requiere `max_digits`+`decimal_places` explícitos; JSON requiere `jq` para leer en consola.
- Deuda técnica: ninguna.
