# Compliance simulado de FairBet Lab

## 1. Integridad financiera

FairBet Lab no maneja dinero real. Todas las operaciones usan moneda virtual con fines educativos. Aun asi, el proyecto adopta controles inspirados en sistemas financieros para evitar inconsistencias y para que el equipo practique buenas decisiones de arquitectura. La regla principal es que todo movimiento debe pasar por un ledger de partida doble. Esto significa que cada deposito, retiro, reserva de apuesta, liquidacion o cashout genera al menos dos entradas contables: una cuenta se debita y otra cuenta se acredita por el mismo monto. La suma global de los movimientos debe permanecer balanceada.

El saldo del usuario no se guarda como un campo editable. Se calcula desde las entradas de `LedgerEntry`, sumando creditos y restando debitos. Esta decision reduce el riesgo de que un saldo quede desincronizado frente al historial contable. Tambien permite auditar cada cambio, porque el origen del balance esta en los movimientos individuales.

Para proteger las operaciones concurrentes se usa `transaction.atomic()`. Esto asegura que un grupo de cambios se confirme completo o se revierta completo. Por ejemplo, una apuesta no deberia crear una `Bet` si antes no se pudo reservar el saldo. Tambien se usa `select_for_update()` cuando se modifica o consulta una cuenta que participa en una operacion financiera. Este bloqueo evita condiciones de carrera, como dos solicitudes simultaneas intentando gastar el mismo saldo.

El sistema trabaja con `Decimal` para montos, cuotas, stakes, payouts y cashout. No se usan `float` en calculos financieros porque los flotantes binarios pueden introducir errores de precision. La precision definida es de cuatro decimales, lo que permite representar fichas virtuales de forma uniforme.

Tambien se implementa idempotencia mediante `transaction_id` o `Idempotency-Key`. Si el usuario repite una solicitud por error, el sistema no debe duplicar el descuento ni la acreditacion. Esto es importante en depositos virtuales, retiros, reservas, liquidaciones y cashout.

## 2. Juego responsable

El proyecto incluye controles de juego responsable, aunque son simulados. El usuario tiene estado de cuenta, puede estar pendiente, verificado, bloqueado o autoexcluido. Las operaciones sensibles exigen cuenta verificada. Un usuario autoexcluido no puede apostar, y la autoexclusion puede registrarse por 7 dias, 30 dias, 90 dias o de forma indefinida.

Tambien existen limites de deposito diario, semanal y mensual. Estos limites buscan representar una barrera preventiva para que el usuario controle su actividad. Cuando se actualizan, el sistema registra cambios y aplica reglas para impedir incrementos inmediatos en ciertos casos. El objetivo educativo es mostrar que el juego responsable no es solo un mensaje en pantalla, sino tambien una regla del dominio.

Las respuestas y templates incluyen avisos visibles. El mensaje principal es: "Juega con responsabilidad. Si crees que tienes un problema, usa la opcion de autoexclusion." Ademas, se muestra el aviso: "Plataforma educativa con moneda virtual. No constituye una casa de apuestas." Estos textos reducen ambiguedad sobre el alcance del proyecto y refuerzan que no existe dinero real.

La auditoria tambien forma parte del control responsable. El sistema crea registros inmutables mediante una cadena de hashes para eventos importantes. Ademas, se agregan reglas simples de actividad sospechosa, como mas de cinco apuestas en menos de sesenta segundos o un deposito seguido de cashout en menos de cinco minutos. Estas reglas no reemplazan un sistema antifraude real, pero ayudan a demostrar como podria empezar un monitoreo de comportamiento.

## 3. Alcance frente a Ley 31557 y DS 005-2023-MINCETUR

FairBet Lab toma como referencia academica la Ley 31557 y el DS 005-2023-MINCETUR, pero no pretende cumplir como operador real. Su alcance es pedagogico: simula conceptos de registro, verificacion, limites, autoexclusion, auditoria, contabilidad interna y reportes de operador. No ofrece apuestas reales, premios reales ni conversion de fichas a dinero.

La partida doble, `transaction.atomic()`, `select_for_update()`, limites de usuario, autoexclusion, mensajes de juego responsable, auditoria y moneda virtual son mecanismos utiles para estudiar el tipo de controles que una plataforma regulada deberia considerar. El dashboard administrativo permite ver metricas como GGR simulado, apuestas pendientes y exposicion por evento. Estas metricas ayudan a entender la operacion, pero no constituyen reporteria regulatoria oficial.

Autocritica honesta: primero, no existe integracion real con una pasarela de pagos, porque el sistema no debe mover dinero. Segundo, no existe validacion KYC real con RENIEC ni otro proveedor oficial; el DNI se valida solo de forma tecnica y simulada. Tercero, no existe certificacion oficial de plataforma, laboratorio homologado ni evaluacion regulatoria externa. Cuarto, no existe monitoreo regulatorio real ni reportes automaticos a una autoridad. Quinto, no se gestionan obligaciones tributarias reales, porque no hay transacciones monetarias ni actividad comercial.

Por estas razones, FairBet Lab debe presentarse siempre como plataforma educativa. Su valor esta en mostrar decisiones tecnicas responsables dentro de un entorno controlado, no en operar como casa de apuestas.
