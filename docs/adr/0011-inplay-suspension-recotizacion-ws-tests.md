# ADR 0011 — In-Play: suspensión de mercado, re-cotización y tests WebSocket

**Fecha:** 2026-05-28
**Autor:** [tu nombre]
**Estado:** Aceptado

---

## Contexto

Con el núcleo (Nivel 1) y las combinadas/cash-out (Nivel 2 parcial) ya funcionando, quedaban
tres huecos explícitos del enunciado para apuestas in-play:

1. Suspensión automática de mercado ante eventos críticos (gol, expulsión).
2. Política de re-cotización: si las odds cambian entre que el usuario abre el ticket y confirma.
3. Tests reales del canal WebSocket (el archivo existente solo probaba el fallback REST).

---

## Opciones consideradas

### Suspensión de mercado

| Opción | Pros | Contras |
|---|---|---|
| **Celery countdown task** (elegida) | Sin polling, preciso, idempotente, fácil de testar con `apply_async` mock | Depende del broker; si Celery cae, el mercado no se reabre |
| Cron/beat cada segundo | Sin dependencia del broker para el reopen | Polling innecesario, latencia de hasta 1s, carga en DB |
| Signal en el model | Rápido de implementar | No permite delay; requeriría sleep en un thread separado |

**Decisión:** `SuspendMarketView` (admin-only) cambia el estado a `SUSPENDIDO` atómicamente
y llama `reopen_market_task.apply_async(countdown=duration_seconds)`.
El default es 30 segundos (decisión del equipo — ver nota al final).
El task hace `select_for_update` y solo reabre si el mercado sigue en `SUSPENDIDO`,
por si un admin lo reabrió manualmente antes.

### Re-cotización

| Opción | Pros | Contras |
|---|---|---|
| **Campo opcional `odds_expected` en el request** (elegida) | Retrocompatible (sin campo = comportamiento anterior), cliente decide cuándo validar | El cliente debe implementar la lógica de enviar el campo |
| Timestamp de cuando se leyeron las odds | Más automático | Requiere modelo extra para rastrear lecturas, complejidad innecesaria |
| Siempre obligatorio | Garantía máxima | Rompe clientes existentes; overhead en todas las apuestas |

**Decisión:** `odds_expected` es un campo opcional en `BetCreateSerializer`.
Si se envía y difiere de `selection.odds` actual, se retorna `HTTP 409 Conflict`
con `odds_expected` y `odds_current` en el body para que el cliente pueda mostrar
el mensaje "las cuotas cambiaron" y pedir reconfirmación.
La comparación ocurre **dentro del `select_for_update`** para que no haya TOCTOU.

### Tests WebSocket

| Opción | Pros | Contras |
|---|---|---|
| **`channels.testing.WebsocketCommunicator`** (elegida) | Oficial de django-channels, prueba el ASGI real | Requiere `pytest-asyncio`, `InMemoryChannelLayer` en conftest |
| Mocks del consumer | Rápido de escribir | No prueba el routing ASGI ni el channel layer real |
| Tests e2e externos (Playwright, wscat) | Prueba desde el navegador | Fuera del scope del test suite de Django |

**Decisión:** `WebsocketCommunicator` con `application` del `asgi.py`.
El `conftest.py` raíz inyecta `InMemoryChannelLayer` en todos los tests para
evitar dependencia de Redis en el CI. `pytest-asyncio` con `asyncio_mode = "auto"`.

---

## Consecuencias

**Se vuelve más fácil:**
- Probar el flujo in-play end-to-end sin Redis real en el CI.
- Suspender un mercado desde el admin panel o via API.
- El cliente frontend puede mostrar "cuotas actualizadas" sin polling adicional.

**Se vuelve más difícil / deuda técnica asumida:**
- Si el worker de Celery está caído cuando se suspende un mercado, el task se perderá
  (a menos que se use `task_acks_late = True` y persistencia de broker). En producción
  se recomienda configurar `CELERY_TASK_SERIALIZER = 'json'` y reintentos con backoff.
- El campo `odds_expected` es opt-in; clientes que no lo envíen no reciben protección
  de re-cotización. Esto es intencional para compatibilidad, pero conviene documentarlo
  en la guía de integración.

---

## Nota sobre la decisión ambigua del enunciado

El enunciado dice "suspensión automática en eventos críticos por N segundos" sin definir N.
**Decisión del equipo:** N = 30 segundos por defecto, configurable vía `duration_seconds`
en el payload del endpoint. El umbral de "cuántos eventos críticos seguidos" disparan la
suspensión queda fuera de este ADR (actualmente es responsabilidad del admin o de un
futuro sistema de detección automática).
