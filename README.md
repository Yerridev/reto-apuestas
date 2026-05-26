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

## Integrantes

- Chilcon Ramirez Abondanyerri
- Chinchay Campos Jhon Jairo
- Puluche Espejo Pietro Ralf
- Bardales Vasquez Keysi Jeanpierre
- Hidrogo Mateo Jeslyn Nicole
