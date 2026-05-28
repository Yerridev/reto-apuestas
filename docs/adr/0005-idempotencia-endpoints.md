# ADR-0005: Idempotencia en endpoints

## Contexto

Las operaciones financieras del sistema pueden repetirse por errores de red, doble clic del usuario o reintentos del cliente. En FairBet Lab esto afecta depositos, retiros, reservas de apuestas, liquidaciones y cashout. Si el backend procesara dos veces la misma solicitud, el ledger podria duplicar descuentos o acreditaciones de moneda virtual.

## Opciones

1. Usar `Idempotency-Key` en el header HTTP.
2. Enviar una clave en el body de cada endpoint.
3. No implementar idempotencia y asumir que el cliente no reintenta.

## Decision

Se usa `Idempotency-Key` como header preferente. En wallet tambien se acepta `idempotency_key` en el body por compatibilidad con los serializers existentes. Internamente la clave se traduce a `transaction_id` y se consulta en `LedgerEntry` o `Bet` antes de crear nuevos movimientos.

## Consecuencias

La misma clave no duplica descuentos ni acreditaciones. La solucion reduce errores por reintentos y mantiene el ledger consistente. La limitacion principal es que la clave debe ser UUID valido en los endpoints de betting. Ademas, el sistema no guarda una tabla separada de idempotencia con payload original, por lo que esta decision cubre el caso financiero principal, pero no compara cuerpos distintos con la misma clave.
