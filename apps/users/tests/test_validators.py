from datetime import date

import pytest
from django.core.exceptions import ValidationError

from apps.users.validators import validate_dni, validate_mayoria_edad


class TestValidateDNI:
    def test_valid_dni(self):
        assert validate_dni('123456781') is None

    def test_dni_with_dv_zero(self):
        assert validate_dni('000000006') is None

    def test_short_dni(self):
        with pytest.raises(ValidationError, match='9 caracteres'):
            validate_dni('1234567')

    def test_long_dni(self):
        with pytest.raises(ValidationError, match='9 caracteres'):
            validate_dni('1234567890')

    def test_alpha_prefix(self):
        with pytest.raises(ValidationError, match='dígitos'):
            validate_dni('ABCDEFGHI')

    def test_wrong_verification_digit(self):
        with pytest.raises(ValidationError, match='Dígito verificador'):
            validate_dni('123456780')

    def test_dni_with_letter_as_dv_correct(self):
        assert validate_dni('12345678E') is None

    def test_dni_with_letter_as_dv_wrong(self):
        with pytest.raises(ValidationError, match='Dígito verificador'):
            validate_dni('12345678X')

    def test_dni_real_user(self):
        assert validate_dni('746960471') is None

    @pytest.mark.parametrize('dni,expected', [
        ('123456781', True),
        ('876543252', True),
        ('102687740', True),
    ])
    def test_multiple_valid_dnis(self, dni, expected):
        if expected:
            assert validate_dni(dni) is None


class TestValidateMayoriaEdad:
    def test_adult(self):
        assert validate_mayoria_edad(date(1990, 1, 1)) is None

    def test_exactly_18(self, monkeypatch):
        monkeypatch.setattr(
            'apps.users.validators.timezone.localdate',
            lambda: date(2013, 1, 1),
        )
        assert validate_mayoria_edad(date(1995, 1, 1)) is None

    def test_underage(self):
        with pytest.raises(ValidationError, match='mayor de 18 años'):
            validate_mayoria_edad(date(2010, 1, 1))

    def test_17_years_old(self, monkeypatch):
        monkeypatch.setattr(
            'apps.users.validators.timezone.localdate',
            lambda: date(2026, 5, 25),
        )
        with pytest.raises(ValidationError, match='mayor de 18 años'):
            validate_mayoria_edad(date(2009, 5, 26))

    def test_birthday_turn_18(self, monkeypatch):
        monkeypatch.setattr(
            'apps.users.validators.timezone.localdate',
            lambda: date(2026, 6, 15),
        )
        assert validate_mayoria_edad(date(2008, 6, 15)) is None
