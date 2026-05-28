# Resumen del Proyecto: FairBet Lab

FairBet Lab es un simulador educativo de apuestas deportivas con moneda virtual. No maneja dinero real y usa reglas de cumplimiento simulado para registro, verificacion de usuarios, juego responsable, auditoria y control de apuestas.

## Stack

| Capa | Tecnologia |
|---|---|
| Backend | Django 5.x |
| API | Django REST Framework |
| Autenticacion | JWT con SimpleJWT |
| Base de datos | PostgreSQL 16 |
| Cache / cola | Redis |
| Tareas | Celery |
| Contenedores | Docker Compose |
| Testing | pytest, pytest-django, pytest-cov, Hypothesis |

## Servicios Docker

| Servicio | Descripcion | Puerto |
|---|---|---|
| `web` | Servidor Django | `8000` |
| `db` | PostgreSQL | `5433` en host, `5432` dentro de Docker |
| `redis` | Redis para cache y Celery | `6379` |
| `celery` | Worker de tareas asincronas | Sin puerto publico |

Nota: el puerto PostgreSQL se publico como `5433` porque ya existe otro servicio local usando `5432`.

## Comandos principales

Levantar servicios:

```bash
docker compose up -d
```

Ver estado:

```bash
docker compose ps
```

Ejecutar migraciones:

```bash
docker compose exec web python manage.py migrate
```

Cargar datos iniciales:

```bash
docker compose exec web python manage.py seedall
```

Ejecutar pruebas:

```bash
docker compose exec web pytest --cov=apps --cov-report=term-missing
```

Apagar servicios:

```bash
docker compose down
```

## URLs principales

| Ruta | Metodo | Descripcion |
|---|---|---|
| `/admin/` | GET | Panel de administracion de Django |
| `/api/auth/register/` | POST | Registro de usuario |
| `/api/auth/me/` | GET | Perfil del usuario autenticado |
| `/api/auth/limits/` | POST | Actualizar limites de juego responsable |
| `/api/auth/self-exclusion/` | POST | Autoexclusion del usuario |
| `/api/auth/verify-account/` | POST | Verificacion de cuenta por admin |
| `/api/token/` | POST | Obtener JWT |
| `/api/token/refresh/` | POST | Refrescar JWT |
| `/api/wallet/deposit/` | POST | Deposito virtual |
| `/api/wallet/balance/` | GET | Saldo de wallet |
| `/api/betting/bets/` | POST | Crear apuesta |
| `/api/betting/events/<event_id>/settle/` | POST | Liquidar evento |
| `/api/audit/verify/` | GET | Verificar integridad de auditoria |

## Apps del proyecto

| App | Responsabilidad |
|---|---|
| `apps.users` | Usuarios, KYC simulado, DNI, edad minima, limites y autoexclusion |
| `apps.wallet` | Wallet virtual, depositos, balance y ledger de partida doble |
| `apps.betting` | Eventos, mercados, cuotas, apuestas y liquidacion |
| `apps.audit` | Auditoria inmutable con cadena de hashes |

## Datos seed

El comando `seedall` crea usuarios, wallets y eventos de prueba.

| Usuario | Password | Rol |
|---|---|---|
| `admin@gmail.com` | `123` | Admin |
| `seed.user1@fairbet.pe` | `Lima2026!` | Usuario verificado |
| `seed.user2@fairbet.pe` | `Cusco2026!` | Usuario verificado |
| `seed.user3@fairbet.pe` | `Arequipa2026!` | Usuario verificado |
| `seed.autoexcluded@fairbet.pe` | `Piura2026!` | Usuario autoexcluido |

Los usuarios verificados reciben wallet y saldo inicial virtual.

## Estructura general

```text
reto-apuestas/
  apps/
    audit/
    betting/
    users/
    wallet/
  config/
    settings.py
    urls.py
    celery.py
    asgi.py
    wsgi.py
  docs/
    adr/
    lecciones.md
    bitacoras y declaraciones
  docker-compose.yml
  docker-compose.override.yml
  Dockerfile
  manage.py
  pyproject.toml
  requirements.txt
  README.md
  RETO-2026.md
```

## Documentacion incluida

| Archivo | Contenido |
|---|---|
| `README.md` | Guia principal del proyecto |
| `RETO-2026.md` | Enunciado y criterios del reto |
| `docs/adr/` | Decisiones de arquitectura |
| `docs/lecciones.md` | Lecciones aprendidas |
| `docs/bitacora-chilcon.md` | Bitacora de trabajo |
| `docs/anti-ai-disclosure-*.md` | Declaraciones de uso de IA |

## Estado actual local

- Carpeta duplicada de backup eliminada.
- Solo queda una carpeta principal: `reto-apuestas`.
- Servicios Docker levantados.
- Migraciones ejecutadas.
- Seed ejecutado.
- API disponible en `http://localhost:8000`.
