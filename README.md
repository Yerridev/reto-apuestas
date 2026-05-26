# FairBet Lab

Simulador educativo de apuestas deportivas con moneda virtual. Cumplimiento normativo simulado (Ley 31557, DS 005-2023-MINCETUR). Sin valor monetario real.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Django 5.x + DRF |
| BD | PostgreSQL 16 |
| Cache/Cola | Redis + Celery *(próximamente)* |
| Tiempo real | Django Channels *(próximamente)* |
| Contenedores | Docker + docker-compose |

## Requisitos

- Docker + Docker Compose

## Inicio rápido

```bash
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Servidor en `http://localhost:8000`.

## Apps

| App | Responsabilidad |
|---|---|
| `apps.wallet` | Contabilidad de partida doble, ledger inmutable |
| `apps.betting` | Ciclo de vida de apuestas, cuotas, liquidación |
| `apps.users` | Registro, KYC simulado (DNI + edad), juego responsable |
| `apps.audit` | Auditoría encadenada por hash, anti-fraude |

## Precisión numérica

Todo monto usa `Decimal(max_digits=18, decimal_places=4)`. Prohibido `float` en operaciones financieras. Constantes en `config.settings.py`.

## Documentación

- `/docs/adr/` — Architecture Decision Records
- `/docs/sketches/` — Bocetos ER y máquinas de estado

## Flujo de trabajo (Git)

### Ramas

| Rama | Propósito |
|---|---|
| `main` | Código entregable. **Solo se mergea via PR con revisión.** |
| `feature/wallet` | Contabilidad de partida doble |
| `feature/betting` | Catálogo, cuotas, apuestas, liquidación |
| `feature/live` | Cuotas en tiempo real + apuestas in-play |
| `feature/audit` | Cadena de auditoría inmutable |
| `feature/anti-fraud` | Detección de actividad sospechosa |
| `feature/dashboard` | Dashboard del operador |

### Reglas

1. **Nunca codees directo en `main`.** Cada funcionalidad nueva va en su rama `feature/*`.
2. **Antes de mergear a `main`**, abrí un Pull Request en GitHub.
3. **El PR necesita al menos 1 aprobación** de otro integrante del equipo para mergear.
4. Commits con **Conventional Commits**: `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`.
5. Tests pasando (`pytest`) antes de abrir el PR.

### Loop diario

```bash
git checkout feature/wallet
# codeás, codeás...
git add . && git commit -m "feat: descripcion del cambio"
git push origin feature/wallet
# En GitHub: abrís PR → pedís review → mergean a main
```

## Integrantes

- Chilcon Ramirez Abondanyerri
- Chinchay Campos Jhon Jairo
- Puluche Espejo Pietro Ralf
- Bardales Vasquez Keysi Jeanpierre
- Hidrogo Mateo Jeslyn Nicole
