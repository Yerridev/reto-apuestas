# ADR 0005 - Estrategia de seed unificado para integracion

- Fecha: 2026-05-28
- Autor: Jeslyn Hidrogo
- Estado: Aceptado

## Contexto

El proyecto necesitaba una forma unica y repetible de poblar datos para pruebas funcionales y demo:

- usuarios con distintos estados de cuenta,
- wallets con saldo inicial,
- eventos y mercados para apuestas.

Tener seeds separados por app dificultaba la integracion y la reproduccion del entorno.

## Opciones consideradas

1. Mantener comandos de seed por app (`seed_events`, etc.) y ejecutarlos manualmente.
- Pros: simple por modulo.
- Contras: propenso a errores operativos; no garantiza orden ni consistencia global.

2. Un comando central `seedall` que orqueste usuarios, wallets y eventos.
- Pros: flujo unico, idempotente y reproducible para todo el equipo.
- Contras: mayor acoplamiento entre apps en el comando.

## Decision

Se adopta la opcion 2: comando `seedall` como punto unico de carga de datos.

## Consecuencias

- Se simplifica el onboarding y la validacion del sistema.
- Se reduce el riesgo de "me falta correr X seed".
- Se asume deuda tecnica de mantener este comando actualizado cuando cambie el dominio.

