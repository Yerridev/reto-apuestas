# FairBet Lab

Simulador educativo de apuestas deportivas con moneda virtual. Cumplimiento normativo simulado (Ley 31557, DS 005-2023-MINCETUR). Sin valor monetario real.

## Stack

| Capa | Tecnologia |
|---|---|
| Backend | Django 5.x + DRF |
| BD | PostgreSQL 16 |
| Cache/Cola | Redis + Celery |
| Tiempo real | Django Channels |
| Contenedores | Docker + docker-compose |

## Requisitos

- Docker + Docker Compose

## Inicio rapido

```bash
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seedall
```

Servidor en `http://localhost:8000`.

## Apps

| App | Responsabilidad |
|---|---|
| `apps.wallet` | Contabilidad de partida doble, ledger inmutable |
| `apps.betting` | Ciclo de vida de apuestas, cuotas, liquidacion |
| `apps.users` | Registro, KYC simulado (DNI + edad), juego responsable |
| `apps.audit` | Auditoria encadenada por hash, anti-fraude |

## Precision numerica

Todo monto usa `Decimal(max_digits=18, decimal_places=4)`. Prohibido `float` en operaciones financieras. Constantes en `config.settings.py`.

## Endpoints clave

- `POST /api/auth/register/`
- `GET /api/auth/me/`
- `POST /api/auth/limits/`
- `POST /api/auth/self-exclusion/`
- `POST /api/auth/verify-account/` (solo admin)
- `POST /api/wallet/deposit/`
- `GET /api/wallet/balance/`
- `POST /api/betting/bets/`
- `POST /api/betting/events/<event_id>/settle/` (solo admin)
- `GET /api/audit/verify/` (solo admin)

## Seed de datos

El comando `seedall` crea usuarios, wallets y eventos:
- 3 usuarios verificados con saldo inicial.
- 1 usuario autoexcluido para pruebas de bloqueo.
- 5 eventos con mercado 1X2 y odds realistas.

```bash
docker compose exec web python manage.py seedall
```

## Cobertura

```bash
docker compose exec web pytest --cov=apps --cov-report=term-missing
```

## Documentacion

- `/docs/adr/` - Architecture Decision Records
- `/docs/sketches/` - Bocetos ER y maquinas de estado

## Flujo de trabajo (Git)

### Ramas

| Rama | Proposito |
|---|---|
| `main` | Codigo entregable. Solo merge via PR con revision. |
| `feature/wallet` | Contabilidad de partida doble |
| `feature/betting` | Catalogo, cuotas, apuestas, liquidacion |
| `feature/live` | Cuotas en tiempo real + apuestas in-play |
| `feature/audit` | Cadena de auditoria inmutable |
| `feature/anti-fraud` | Deteccion de actividad sospechosa |
| `feature/dashboard` | Dashboard del operador |
| `feature/seed` | Users fixes + seed + Docker |

### Reglas

1. Nunca codees directo en `main`. Cada funcionalidad nueva va en su rama `feature/*`.
2. Antes de mergear a `main`, abre un Pull Request en GitHub.
3. El PR necesita al menos 1 aprobacion de otro integrante del equipo.
4. Commits con Conventional Commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`.
5. Tests pasando (`pytest`) antes de abrir el PR.

## Integrantes

- Chilcon Ramirez Abondanyerri
- Chinchay Campos Jhon Jairo
- Puluche Espejo Pietro Ralf
- Bardales Vasquez Keysi Jeanpierre
- Hidrogo Mateo Jeslyn Nicole

## Checklist de entrega

- [ ] `docker compose up` levanta sin errores
- [ ] tests `pytest` en verde
- [ ] cobertura >= 80% en `apps/wallet` y `apps/betting`
- [ ] seed funcionando (usuarios + eventos + wallets)

---
Plataforma educativa con moneda virtual. No constituye una casa de apuestas.
