# ADR-0002: Autenticación JWT con SimpleJWT

**Fecha:** 2026-05-25 | **Autor:** FairBet Lab (Grupo C2)

## Contexto
Definir el mecanismo de autenticación para la API REST antes de exponer endpoints de negocio.

## Opciones consideradas

| Opción | Pro | Contra |
|--------|-----|--------|
| **Session (Django default)** | Zero-config, CSRF nativo, sesión en servidor | Stateful (escala horizontal requiere sesión compartida), no apto para SPA/mobile sin cookies same-site |
| **JWT (SimpleJWT)** | Stateless, cualquier cliente (SPA, mobile) funciona, refresh rotation | Librería externa, manejo de expiración y refresh del lado cliente, vulnerable a XSS si se almacena mal |

## Decisión
JWT con `djangorestframework-simplejwt`. Access token 1h, refresh token 7d con rotation. `JSONRenderer` exclusivo (sin Browsable API en producción).

## Consecuencias
- [+] Sin estado en servidor; cualquier cliente consume la API sin fijar dominio.
- [+] Refresh rotation anula tokens viejos automáticamente.
- [+] Rate limiting agresivo (3/h registro, 10/m anónimo, 100/m autenticado).
- [-] El frontend debe gestionar expiración y refresh de tokens.
- [-] Sin Browsable API (dificulta debug manual; se compensa con OpenAPI posterior).
