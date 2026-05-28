# Prompt para Bardales — Infraestructura + Seed (`feature/seed`)

## Contexto actual (main)

| App | Integrante | Estado |
|---|---|---|
| `apps.wallet` | Chilcon | ✅ Listo — partida doble, depositar, balance, idempotencia |
| `apps.betting` | Chinchay | ✅ Listo — eventos, mercados, apuestas, liquidación |
| `apps.audit` | Puluche | ✅ Listo — hash chain, signals conectados a wallet+betting |
| `apps.users` | Chilcon | ✅ Listo — auth JWT, DNI RENIEC, KYC, auto-verificar |

**ADRs existentes**: 0001, 0002, 0003, 0004, 0006, 0007, 0008 (en `docs/adr/`)
**Sketches**: ❌ No existen aún
**Seed**: ❌ Solo `seed_events` en betting, falta unificado
**docker-compose**: solo PG + web, sin Redis ni Celery

---

## Tareas (I-01 a I-05)

### I-01 — Endpoint verificar cuenta (SKIP / repensar)

Original: `POST /api/auth/verify/{user_id}/`
Ahora: RegisterSerializer ya setea `account_status = VERIFICADO` automáticamente al crear.

**Opción A**: saltarlo (no hace falta si ya se auto-verifica).
**Opción B**: dejarlo como endpoint admin para forzar verificación manual de cualquier usuario.

Si elegís B:
- Solo admin puede acceder
- Cambia `account_status` → `VERIFICADO`
- Reader: `apps/users/views.py`, `apps/users/serializers.py`, `apps/users/urls.py`

---

### I-02 — docker-compose completo

Agregar **Redis** + **Celery worker** al `docker-compose.yml`.

Estado actual: solo `db` + `web`.

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  celery:
    build: .
    command: celery -A config worker -l info
    volumes:
      - .:/app
    environment:
      DJANGO_SETTINGS_MODULE: config.settings
      # ...mismas env vars que web
    depends_on:
      - db
      - redis
      - web
```

Verificar que `docker compose up` levanta sin errores.

**Archivos a tocar**: `docker-compose.yml`, opcionalmente `config/settings.py` (agregar `CELERY_BROKER_URL`)

---

### I-03 — Seed completo (`seedall` command)

Crear `apps/betting/management/commands/seedall.py`

Debe crear:
1. **3 usuarios verificados** con DNI válido y saldo inicial en wallet
2. **1 usuario autoexcluido** (para probar bloqueo)
3. **5 eventos deportivos** con mercados 1X2 y odds realistas
4. **Wallets con saldo inicial** para cada usuario verificado (vía `deposit()`)

DNIs válidos para seed:
- `746960471` → peso 2, check digit `1` (RENIEC lookup table)
- `102687760` → check según tabla
- `123456781` → check digit `1` (el del conftest)

Usar las funciones de wallet:
```python
from apps.wallet.services import deposit, get_or_create_wallet
```

Verificar:
```bash
docker compose exec web python manage.py seedall
docker compose exec web python manage.py shell -c "from apps.users.models import User; print(User.objects.count())"
```

---

### I-04 — Reporte de cobertura

```bash
docker compose exec web python -m pytest --cov=apps --cov-report=html --cov-report=term
```

Requisito: **≥ 80%** en `apps/wallet` y `apps/betting`.

Si no llega, agregar tests faltantes en los test files existentes.

El reporte HTML queda en `htmlcov/index.html`.

---

### I-05 — README final

Actualizar `README.md`:
- ✅ Quitar "(próximamente)" de Redis, Celery, Channels
- ✅ Agregar instrucciones de seed: `docker compose exec web python manage.py seedall`
- ✅ Tabla de endpoints disponibles (o link a docs)
- ✅ Agregar footer educativo: *"Plataforma educativa con moneda virtual. No constituye una casa de apuestas."*
- ✅ Checklist de entrega actualizado

---

## Checklist de entrega (tu parte)

- [ ] `docker compose up` levanta sin errores
- [ ] `pytest` pasa al 100%
- [ ] Cobertura ≥80% en wallet y betting
- [ ] Seed funciona: usuarios + eventos + wallets
- [ ] Footer educativo en el README
- [ ] Tu `docs/anti-ai-disclosure.md` firmado

---

## Branch workflow

```bash
git checkout main
git pull origin main                       # main actualizado con wallet+betting+audit
git checkout -b feature/seed
# ... codeás ...
git add . && git commit -m "feat: seedall command [ai-assisted]"
git push origin feature/seed
# En GitHub: abrís PR → pedís review → merge a main
```

**Importante**: Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
**Si usaste IA**: agregar sufijo `[ai-assisted]` en el commit.

---

## Archivos clave que ya existen

| Archivo | Qué tiene |
|---|---|
| `apps/wallet/services.py` | `deposit()`, `get_balance()`, `reserve_for_bet()`, `settle_win()`, `settle_loss()` |
| `apps/betting/management/commands/seed_events.py` | Seed parcial de eventos (referencia para `seedall`) |
| `apps/users/tests/conftest.py` | Fixtures de usuario (DNI `123456781`) |
| `config/settings.py` | Config Django, REST Framework, JWT |
| `config/urls.py` | Rutas de wallet, betting, audit, auth |
| `docker-compose.yml` | Actual: solo db + web |

---

## Tiempo estimado

| Tarea | Min |
|---|---|
| I-01 (si aplica) | 25 |
| I-02 docker-compose | 30 |
| I-03 seedall | 25 |
| I-04 cobertura | 15 |
| I-05 README | 20 |
| anti-ai-disclosure | 5 |
| **Total** | **~2h** |
