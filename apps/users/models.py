from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.users.choices import AccountStatus, ExclusionType
from apps.users.managers import UserManager
from apps.users.validators import validate_dni, validate_mayoria_edad


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        unique=True,
        verbose_name=_('correo electrónico'),
        max_length=254,
    )
    dni = models.CharField(
        max_length=9,
        unique=True,
        validators=[validate_dni],
        verbose_name=_('DNI'),
    )
    first_name = models.CharField(
        max_length=30,
        verbose_name=_('nombres'),
    )
    last_name = models.CharField(
        max_length=30,
        verbose_name=_('apellidos'),
    )
    birth_date = models.DateField(
        validators=[validate_mayoria_edad],
        verbose_name=_('fecha de nacimiento'),
    )
    account_status = models.CharField(
        max_length=25,
        choices=AccountStatus.choices,
        default=AccountStatus.PENDIENTE_VERIFICACION,
        verbose_name=_('estado de cuenta'),
    )
    deposit_limit_daily = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=settings.DECIMAL_PLACES,
        null=True,
        blank=True,
        verbose_name=_('límite diario de depósito'),
    )
    deposit_limit_weekly = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=settings.DECIMAL_PLACES,
        null=True,
        blank=True,
        verbose_name=_('límite semanal de depósito'),
    )
    deposit_limit_monthly = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=settings.DECIMAL_PLACES,
        null=True,
        blank=True,
        verbose_name=_('límite mensual de depósito'),
    )
    deposit_limit_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('última modificación de límites'),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('activo'),
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name=_('staff'),
    )
    date_joined = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('fecha de registro'),
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['dni', 'first_name', 'last_name', 'birth_date']

    class Meta:
        verbose_name = _('usuario')
        verbose_name_plural = _('usuarios')

    def __str__(self):
        return f'{self.get_full_name()} ({self.dni})'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_short_name(self):
        return self.first_name


class SelfExclusion(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='self_exclusions',
        verbose_name=_('usuario'),
    )
    exclusion_type = models.CharField(
        max_length=15,
        choices=ExclusionType.choices,
        verbose_name=_('tipo de exclusión'),
    )
    start_date = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('fecha de inicio'),
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('fecha de fin'),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('creado en'),
    )

    class Meta:
        verbose_name = _('autoexclusión')
        verbose_name_plural = _('autoexclusiones')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} - {self.get_exclusion_type_display()}'


class DepositLimitChange(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='limit_changes',
        verbose_name=_('usuario'),
    )
    field_name = models.CharField(
        max_length=30,
        verbose_name=_('campo modificado'),
    )
    old_value = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=settings.DECIMAL_PLACES,
        null=True,
        blank=True,
        verbose_name=_('valor anterior'),
    )
    new_value = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=settings.DECIMAL_PLACES,
        null=True,
        blank=True,
        verbose_name=_('valor nuevo'),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('creado en'),
    )

    class Meta:
        verbose_name = _('cambio de límite')
        verbose_name_plural = _('cambios de límites')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} - {self.field_name}: {self.old_value} → {self.new_value}'
