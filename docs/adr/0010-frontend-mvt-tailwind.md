# ADR-0010: Frontend MVT con Tailwind

## Contexto

El equipo trabaja principalmente con Python y Django. El tiempo de entrega es limitado y el proyecto ya tiene backend, API, Docker y tests como prioridad.

## Opciones

1. Crear frontend con React o Vue.
2. Crear frontend con Django Templates y Tailwind CDN.
3. No crear frontend y dejar solo API.

## Decision

Se usa Django Templates bajo el patron MVT y Tailwind CDN. Las paginas usan vistas Django, formularios HTML y servicios existentes de wallet y betting.

## Consecuencias

La complejidad operativa baja porque no hay build frontend, bundler ni despliegue separado. La interfaz es menos interactiva que una SPA, pero suficiente para registro, login, wallet, apuestas, historial, perfil y dashboard admin. Tailwind CDN no es ideal para produccion, pero es adecuado para el alcance academico y permite iterar rapido.
