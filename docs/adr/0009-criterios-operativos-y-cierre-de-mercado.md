# ADR 0009 - Criterios operativos para cierre de mercado y liquidacion

- Fecha: 2026-05-28
- Autor: Jeslyn Hidrogo
- Estado: Aceptado

## Contexto

En apuestas deportivas, las decisiones de cierre de mercado y liquidacion impactan
integridad financiera, experiencia de usuario y trazabilidad regulatoria.

Se necesitaba definir reglas explicitas para:

- cuando impedir nuevas apuestas,
- cuando liquidar apuestas existentes,
- como manejar estados `suspendido` y `anulado`.

## Opciones consideradas

1. Reglas flexibles definidas manualmente por operador en cada caso.
- Pros: maxima libertad operativa.
- Contras: alta variabilidad, dificulta auditoria e incrementa riesgo de inconsistencias.

2. Reglas predefinidas por estado de evento/mercado y transiciones de apuesta.
- Pros: comportamiento predecible, auditable y testeable.
- Contras: menor flexibilidad ante casos excepcionales.

## Decision

Se adopta la opcion 2 con criterios operativos fijos:

- Evento `programado` + mercado `abierto`: permite apostar.
- Evento iniciado o mercado `cerrado/suspendido`: rechaza nuevas apuestas.
- Liquidacion solo cuando el evento tiene resultado oficial y estado final.
- Estado `anulado`: aplica anulacion de apuesta segun reglas del modulo betting.

## Consecuencias

- Mejora trazabilidad de decisiones operativas.
- Reduce ambiguedad en soporte y pruebas.
- Requiere documentar excepciones fuera de la regla en auditoria cuando ocurran.

