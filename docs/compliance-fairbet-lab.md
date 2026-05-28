# FairBet Lab - Documento de compliance y operacion

## 1. Alcance y naturaleza de la plataforma

FairBet Lab es una plataforma educativa de apuestas deportivas con moneda virtual.
No integra pasarelas de pago reales y no convierte fichas virtuales a dinero.

Mensaje operativo obligatorio:
"Plataforma educativa con moneda virtual. No constituye una casa de apuestas."

Este alcance limita deliberadamente la exposicion legal y alinea la implementacion
con objetivos de aprendizaje en integridad financiera, concurrencia y trazabilidad.

## 2. Integridad financiera

La plataforma aplica contabilidad de partida doble en `apps/wallet`:

- Cada operacion genera entradas balanceadas `DEBIT/CREDIT`.
- El saldo nunca se persiste como campo, siempre se deriva por agregacion.
- Se usa `Decimal(18,4)` en todos los montos para precision exacta.

Invariantes verificadas:

- suma global de debitos y creditos = 0,
- no saldo negativo por reservas concurrentes,
- payout calculado como `stake * odds` sin `float`.

Estas reglas reducen riesgo de doble gasto y de inconsistencias contables.

## 3. KYC simulado y control de acceso

El modulo `apps/users` incorpora:

- validacion de DNI peruano con digito verificador,
- validacion de mayoria de edad,
- autenticacion JWT para APIs protegidas.

Estados de cuenta:

- `pendiente_verificacion`,
- `verificado`,
- `bloqueado`,
- `autoexcluido`.

Se mantiene endpoint administrativo de verificacion de cuenta para escenarios
operativos donde se requiera control manual.

## 4. Juego responsable

Controles funcionales implementados:

- limites de deposito por periodo (diario, semanal, mensual),
- control de subida de limites con cooldown de 24 horas,
- autoexclusion temporal o indefinida con bloqueo efectivo.

Objetivo de compliance:

- prevenir escalamiento impulsivo de gasto,
- permitir evidencia auditable de cambios de limites,
- bloquear la operativa de cuentas autoexcluidas.

## 5. Ciclo de vida de apuesta y consistencia operativa

En `apps/betting` se implementa maquina de estados con transiciones validadas.
El sistema rechaza apuestas cuando:

- la cuenta no esta habilitada,
- no hay saldo suficiente,
- el evento ya inicio,
- el mercado no esta abierto.

Liquidacion:

- estado y resultado son controlados por endpoint admin,
- apuesta ganada/perdida actualiza wallet conforme al flujo contable.

Esto evita reglas ambiguas de negocio y facilita defensa tecnica en revision.

## 6. Auditoria inmutable y trazabilidad

`apps/audit` registra eventos relevantes mediante hash chain:

- cada registro contiene hash previo,
- cualquier alteracion posterior rompe la cadena.

Ademas, hay endpoint de verificacion de integridad para operador/admin.
Este mecanismo permite control de no repudio dentro del alcance educativo.

## 7. Operacion tecnica y despliegue local

El `docker-compose.yml` integra:

- `db` (PostgreSQL),
- `web` (Django),
- `redis`,
- `celery`.

Con esto, el entorno de ejecucion es repetible para desarrollo, pruebas y demo.
El comando `seedall` habilita carga inicial de usuarios, wallets y eventos.

## 8. Riesgos abiertos y mitigacion

Riesgos vigentes:

- Politicas antifraude avanzadas no cubiertas en totalidad.
- Controles de observabilidad aun en nivel base.
- Falta de componentes de tiempo real avanzados en esta etapa.

Mitigaciones aplicadas:

- pruebas automáticas sobre invariantes criticas,
- auditoria encadenada,
- reglas de estado y permisos admin en operaciones sensibles.

## 9. Conclusiones

La solucion actual cumple los pilares del nivel 1 del reto:

- integridad financiera verificable,
- control de concurrencia,
- trazabilidad de eventos criticos,
- controles de juego responsable.

Persisten items de evolucion para una siguiente iteracion (nivel 2/3 completo),
pero el estado actual es defendible en revision tecnica y funcional.

