# ADR-0004: Estrategia de concurrencia — select_for_update

**Fecha:** 2026-05-27 | **Autor:** Chilcon Ramirez Abodanyerri (Grupo 06)

## Contexto

Un usuario podría hacer varias apuestas al mismo tiempo (o dos tabs abiertos, o dos
requests en paralelo). Si los dos requests leen el saldo al mismo tiempo, los dos ven
saldo suficiente, y los dos descuentan — el saldo termina negativo. Eso se llama
doble gasto y hay que evitarlo.

## Opciones consideradas

**Opción A — Bloqueo optimista (campo `version`)**
Se agrega un campo `version` al modelo. Antes de escribir, verificas que el `version`
no cambió desde que lo leíste. Si cambió, reintentás. El problema es que bajo alta
contención hay muchos reintentos y la lógica de retry se complica. Además el reto
pide explícitamente `select_for_update`, así que esta opción quedó descartada rápido.

**Opción B — Bloqueo pesimista (`select_for_update`)**
PostgreSQL bloquea la fila desde que la lees hasta que terminas el `transaction.atomic()`.
Cualquier otro request que quiera esa misma fila tiene que esperar. Garantía fuerte,
sin reintentos, y Django lo soporta directo con `.select_for_update()`.

## Decisión

Elegimos la **Opción B**. En toda operación que lee el saldo antes de gastar, usamos:

```python
with transaction.atomic():
    entradas = LedgerEntry.objects.select_for_update().filter(
        account__user=user,
        account__type=AccountType.WALLET_USUARIO,
    )
    saldo = calcular_saldo(entradas)
    if saldo < monto:
        raise SaldoInsuficiente()
    # crear las entradas balanceadas aquí
```

Esto garantiza que dos requests simultáneos se ejecutan en serie, no en paralelo.

## Consecuencias

- Bueno: no hay doble gasto, punto. La garantía es a nivel de base de datos.
- Bueno: los tests de concurrencia con `threading` son predecibles porque las
  operaciones quedan serializadas.
- Bueno: cumple el requisito explícito del reto.
- Malo: si hay mucha contención en un usuario (poco probable en una plataforma
  educativa), los requests se encolan y algunos pueden tardar más.
- Malo: requiere PostgreSQL. Ya lo teníamos decidido en ADR-0001 así que no es
  problema nuevo.
- Deuda técnica: a escala real habría que evaluar sharding por usuario para
  reducir contención, pero eso está fuera del alcance de este reto.
