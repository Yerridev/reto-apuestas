# ADR-0009: Re-cotizacion de odds

## Contexto

En una plataforma de apuestas, la cuota puede cambiar entre el momento en que el usuario abre el ticket y el momento en que confirma la apuesta. FairBet Lab es educativo y no implementa feeds de cuotas en tiempo real.

## Opciones

1. Re-cotizar en tiempo real antes de confirmar.
2. Rechazar la apuesta si la cuota cambio.
3. Bloquear la cuota al momento de crear la apuesta.

## Decision

La cuota se bloquea al momento de crear la `Bet`. El campo `odds` de la apuesta guarda un snapshot de `Selection.odds` en ese instante. Las liquidaciones y cashout usan ese valor congelado.

## Consecuencias

La implementacion es simple, auditable y suficiente para el reto academico. No se implementa re-cotizacion en tiempo real. La deuda tecnica es agregar una confirmacion explicita cuando la cuota cambie antes de apostar, junto con un canal live para cuotas.
