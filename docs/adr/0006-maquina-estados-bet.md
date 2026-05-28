# ADR-0006: Maquina de estados de Bet

## Contexto

El modulo de apuestas necesita representar el ciclo de vida de una apuesta sin romper la contabilidad de partida doble. Una apuesta aceptada reserva fondos en `apps.wallet`; una apuesta liquidada ya no puede cambiar porque duplicaria o revertiria movimientos del ledger.

## Opciones

1. Guardar solo un campo libre `status` y validar las transiciones en cada endpoint.
2. Centralizar los estados y transiciones validas en `apps.betting.choices`.
3. Modelar cada estado como una tabla separada.

## Decision

Se centraliza la maquina de estados en `BetStatus` y `can_transition`. La unica transicion de salida permitida es:

- `accepted -> settled_won`
- `accepted -> settled_lost`
- `accepted -> cancelled`

Los estados `settled_won`, `settled_lost` y `cancelled` son terminales.

## Consecuencias

- La regla queda cubierta por tests unitarios y property-based testing.
- Los endpoints no pueden cambiar una apuesta ya liquidada.
- La integracion con wallet es mas segura porque cada liquidacion ocurre una sola vez.
- Nuevos estados futuros deberan agregarse explicitamente a la tabla de transiciones.
