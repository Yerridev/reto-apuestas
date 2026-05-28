from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.users.choices import AccountStatus
from apps.users.models import DepositLimitChange, SelfExclusion

User = get_user_model()


class TestUserManager:
    def test_create_user(self, db):
        user = User.objects.create_user(
            email='user@test.com',
            dni='123456781',
            first_name='John',
            last_name='Doe',
            birth_date=date(1990, 1, 1),
            password='pass123!',
        )
        assert user.email == 'user@test.com'
        assert user.dni == '123456781'
        assert user.first_name == 'John'
        assert user.account_status == AccountStatus.PENDIENTE_VERIFICACION
        assert not user.is_staff
        assert not user.is_superuser
        assert user.check_password('pass123!')

    def test_create_user_without_email_raises_error(self, db):
        with pytest.raises(ValueError, match='correo electrónico'):
            User.objects.create_user(
                email='',
                dni='123456781',
                first_name='John',
                last_name='Doe',
                birth_date=date(1990, 1, 1),
                password='pass123!',
            )

    def test_create_user_without_dni_raises_error(self, db):
        with pytest.raises(ValueError, match='DNI'):
            User.objects.create_user(
                email='user@test.com',
                dni='',
                first_name='John',
                last_name='Doe',
                birth_date=date(1990, 1, 1),
                password='pass123!',
            )

    def test_create_user_invalid_dni_raises_error(self, db):
        with pytest.raises(ValidationError):
            User.objects.create_user(
                email='user@test.com',
                dni='123456780',
                first_name='John',
                last_name='Doe',
                birth_date=date(1990, 1, 1),
                password='pass123!',
            )

    def test_create_user_underage_raises_error(self, db):
        with pytest.raises(ValidationError):
            User.objects.create_user(
                email='young@test.com',
                dni='123456781',
                first_name='Young',
                last_name='User',
                birth_date=date(2010, 1, 1),
                password='pass123!',
            )

    def test_create_superuser(self, db):
        admin = User.objects.create_superuser(
            email='admin@test.com',
            dni='876543252',
            first_name='Admin',
            last_name='Test',
            birth_date=date(1990, 1, 1),
            password='admin123!',
        )
        assert admin.is_staff
        assert admin.is_superuser
        assert admin.account_status == AccountStatus.VERIFICADO


class TestUserModel:
    def test_str_representation(self, user):
        assert str(user) == 'Test User (123456781)'

    def test_get_full_name(self, user):
        assert user.get_full_name() == 'Test User'

    def test_get_short_name(self, user):
        assert user.get_short_name() == 'Test'

    def test_email_as_username_field(self):
        assert User.USERNAME_FIELD == 'email'

    def test_unique_email(self, db, user):
        with pytest.raises(Exception):
            User.objects.create_user(
                email='test@example.com',
                dni='87654325',
                first_name='Other',
                last_name='User',
                birth_date=date(1990, 1, 1),
                password='pass123!',
            )

    def test_unique_dni(self, db, user):
        with pytest.raises(Exception):
            User.objects.create_user(
                email='other@example.com',
                dni='123456781',
                first_name='Other',
                last_name='User',
                birth_date=date(1990, 1, 1),
                password='pass123!',
            )


class TestSelfExclusion:
    def test_create_temporal(self, db, user):
        now = timezone.now()
        exclusion = SelfExclusion.objects.create(
            user=user,
            exclusion_type='7_dias',
            start_date=now,
            end_date=now + timedelta(days=7),
        )
        assert exclusion.user == user
        assert exclusion.exclusion_type == '7_dias'
        assert exclusion.end_date is not None

    def test_create_indefinite(self, db, user):
        exclusion = SelfExclusion.objects.create(
            user=user,
            exclusion_type='indefinida',
        )
        assert exclusion.end_date is None

    def test_str(self, db, user):
        exclusion = SelfExclusion.objects.create(
            user=user,
            exclusion_type='30_dias',
        )
        assert str(exclusion) == 'test@example.com - 30 días'


class TestDepositLimitChange:
    def test_create_record(self, db, user):
        change = DepositLimitChange.objects.create(
            user=user,
            field_name='deposit_limit_daily',
            old_value=None,
            new_value='500.0000',
        )
        assert change.user == user
        assert change.old_value is None
        assert str(change.new_value) == '500.0000'

    def test_str(self, db, user):
        change = DepositLimitChange.objects.create(
            user=user,
            field_name='deposit_limit_daily',
            old_value='500.0000',
            new_value='200.0000',
        )
        assert 'test@example.com' in str(change)
