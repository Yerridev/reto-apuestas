# ADR-0007: Auditoria inmutable con hash chain

## Contexto

La plataforma necesita trazabilidad regulatoria sobre movimientos de wallet, apuestas y cambios relevantes del sistema. El reto menciona cumplimiento alineado con la Ley 31557, por lo que no basta con guardar eventos sueltos: tambien debemos poder detectar manipulacion posterior de registros.

## Opciones consideradas

1. Tabla append-only simple.
   Pros: implementacion directa y barata.
   Contras: si alguien modifica filas en base de datos, la alteracion no se detecta facilmente.

2. Hash chain por registro usando SHA256.
   Pros: cada evento queda enlazado con el anterior y cualquier cambio rompe la cadena.
   Contras: complica un poco la escritura y exige un proceso explicito de verificacion.

3. Logging externo en otro servicio.
   Pros: mejor aislamiento y mas dificil de alterar desde la app principal.
   Contras: aumenta complejidad operativa y sale del alcance del challenge actual.

## Decision

Se adopta una tabla `AuditLog` con hash chain basada en SHA256. Cada registro guarda su `prev_hash` y su `hash` calculado sobre `prev_hash + payload serializado`. El primer registro usa `prev_hash = '0'`.

## Consecuencias

- Cualquier manipulacion posterior de `payload`, `prev_hash` o `hash` se detecta al verificar la cadena.
- Wallet y betting pueden emitir eventos auditables automaticamente mediante signals.
- La auditoria queda dentro del mismo sistema y es suficiente para el alcance del reto.
- Como contrapartida, los registros no deben editarse ni borrarse en flujo normal; la trazabilidad depende de mantener el historial completo.
