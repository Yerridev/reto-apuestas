# ADR-0003: Modelo de wallet con partida doble

**Fecha:** 2026-05-27 | **Autor:** Chilcon Ramirez Abodanyerri (Grupo 06)

## Contexto

Necesitábamos decidir cómo guardar los movimientos de dinero virtual del wallet. El reto
pide que el saldo nunca se guarde como un campo directo, sino que siempre se calcule a
partir de los movimientos. También pide que toda operación sea trazable y que se pueda
verificar que la suma global de débitos y créditos es siempre cero.

## Opciones consideradas

**Opción A — Campo `balance` en el modelo User**
Lo más simple: un campo `balance` que se actualiza con cada operación. El problema es que
si una operación falla a medias, el saldo puede quedar inconsistente. Además no hay historial,
solo el valor actual. No cumple lo que pide el reto.

**Opción B — Tabla de movimientos con partida doble**
Cada operación genera al menos dos entradas en una tabla `LedgerEntry`: una en la cuenta de
origen y otra en la cuenta de destino. El saldo se calcula siempre con:

```
balance = SUM(credits) - SUM(debits)
```

Si algo falla, la transacción atómica lo revierte todo. El historial queda completo.

## Decisión

Elegimos la **Opción B**. Implementamos dos modelos:

- `Account`: representa una cuenta contable. Los tipos son `wallet_usuario`, `casa`,
  `apuestas_pendientes` y `bonos`.
- `LedgerEntry`: cada movimiento individual con los campos `account`, `amount`
  (`Decimal(18,4)`), `direction` (`DEBIT` o `CREDIT`), `transaction_id` (UUID para
  evitar duplicados) y `created_at`.

Toda operación financiera crea mínimo dos entradas balanceadas dentro de una
`transaction.atomic()`. El saldo nunca se almacena; siempre se deriva con una query.

## Consecuencias

- Bueno: el saldo siempre es correcto porque se calcula de los movimientos reales.
  Si la BD está bien, el wallet está bien.
- Bueno: facilita mucho los tests con `hypothesis` porque la invariante es simple:
  la suma de todas las entradas tiene que ser cero.
- Bueno: cada movimiento queda registrado con timestamp, lo que conecta bien con
  la auditoría hash-chain que va a implementar Puluche (ADR-0007).
- Malo: cada operación escribe al menos 2 filas en vez de 1 `UPDATE`. Para una
  plataforma educativa no es problema, pero hay que tenerlo en cuenta.
- Deuda técnica: si el volumen crece mucho, se podría agregar una vista materializada
  del saldo por usuario sin tocar el modelo base.
