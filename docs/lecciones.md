# Lecciones aprendidas

## Sprint 1 (25–31 Mayo 2026)

### Intento fallido 1: Validators en extra_kwargs del serializer

**Qué pasó:** Puse los validators del DNI y la edad dentro de `extra_kwargs` en el `RegisterSerializer`. Los tests de registro duplicado fallaban con 500 Internal Server Error en vez de 400.

**Por qué falló:** DRF toma la clave `validators` de `extra_kwargs` y REEMPLAZA los validators auto-generados (como `UniqueValidator` para DNI y email), no los fusiona. El DNI duplicado llegaba a la base de datos sin validación previa y explotaba con `IntegrityError`.

**Qué aprendí:** Para validación custom en DRF hay que usar métodos `validate_<campo>()` en el serializer. No usar `extra_kwargs` con `validators` a menos que quieras reemplazar completamente la validación del campo.

### Intento fallido 2: No llamar full_clean() en el manager

**Qué pasó:** Creaba usuarios con DNI inválido o menores de edad y el sistema los aceptaba sin error.

**Por qué falló:** Django NO ejecuta los `validators` del modelo en `save()`. Solo se ejecutan cuando llamás `full_clean()` explícitamente. El `UserManager.create_user()` hacía `user.save()` sin pasar por `full_clean()`.

**Qué aprendí:** El manager debe llamar `user.full_clean()` antes de `user.save()`. Es un bug silencioso muy común en Django.

### Intento fallido 3: Throttle rate agotado en tests

**Qué pasó:** Los tests de registro fallaban con 429 Too Many Requests después del tercer test, aunque las validaciones eran correctas.

**Por qué falló:** DRF cuenta TODAS las peticiones contra el rate limit, incluso las que fallan con 400. El throttle de registro (3/hour) se agotaba después de 3 tests, y los siguientes recibían 429.

**Qué aprendí:** En tests hay que deshabilitar el throttle o subir los rates drásticamente con `settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`. Lo resolví con un fixture `autouse` en `conftest.py`.

### Intento fallido 4: DNI de 8 caracteres en tests

**Qué pasó:** Usaba DNI como `'87654325'` (solo 8 dígitos) en los tests y la validación fallaba porque el validador espera 9 caracteres con dígito verificador.

**Por qué falló:** El DNI peruano tiene 8 dígitos + 1 dígito verificador = 9 caracteres. Los tests usaban cadenas de 8 sin calcular el DV.

**Qué aprendí:** Calcular el DV correctamente para cada DNI de prueba. Para `87654325`, el DV es `7` (módulo 11 con pesos [3,2,7,6,5,4,3,2]), así que el DNI completo debe ser `876543257`.
