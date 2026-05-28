from datetime import date

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def validate_dni(value):
    if len(value) != 9:
        raise ValidationError(
            _('El DNI debe tener 9 caracteres (8 dígitos + 1 dígito verificador).'),
        )
    if not value[:8].isdigit():
        raise ValidationError(
            _('Los primeros 8 caracteres del DNI deben ser dígitos.'),
        )

    pesos = [3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(value[i]) * pesos[i] for i in range(8))
    residuo = suma % 11
    resultado = 11 - residuo
    if resultado == 11:
        resultado = 0

    digito_ingresado = value[8].upper()
    tabla_numerica = '67890112345'
    tabla_alfabetica = 'KABCDEFGHIJ'
    tabla = tabla_alfabetica if digito_ingresado.isalpha() else tabla_numerica

    if digito_ingresado != tabla[resultado]:
        raise ValidationError(
            _('Dígito verificador inválido para el DNI ingresado.'),
        )


def validate_mayoria_edad(birth_date):
    today = timezone.localdate()
    age = today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )
    if age < 18:
        raise ValidationError(
            _('Debe ser mayor de 18 años para registrarse.'),
        )
