import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.betting.choices import BetStatus, can_transition


class Event(models.Model):
    class Status(models.TextChoices):
        PROGRAMADO = 'programado', 'Programado'
        EN_VIVO = 'en_vivo', 'En vivo'
        FINALIZADO = 'finalizado', 'Finalizado'
        SUSPENDIDO = 'suspendido', 'Suspendido'
        ANULADO = 'anulado', 'Anulado'

    name = models.CharField(max_length=200, verbose_name=_('nombre'))
    sport = models.CharField(max_length=100, verbose_name=_('deporte'))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROGRAMADO,
        verbose_name=_('estado'),
    )
    starts_at = models.DateTimeField(verbose_name=_('inicia en'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('creado en'))

    class Meta:
        verbose_name = _('evento')
        verbose_name_plural = _('eventos')
        ordering = ['starts_at']

    def __str__(self):
        return f'{self.name} ({self.sport})'


class Market(models.Model):
    class Type(models.TextChoices):
        UNO_X_DOS = '1X2', '1X2'
        OVER_UNDER = 'over_under', 'Over/Under'
        BTTS = 'btts', 'Both teams to score'

    class Status(models.TextChoices):
        ABIERTO = 'abierto', 'Abierto'
        CERRADO = 'cerrado', 'Cerrado'
        SUSPENDIDO = 'suspendido', 'Suspendido'
        LIQUIDADO = 'liquidado', 'Liquidado'

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='markets',
        verbose_name=_('evento'),
    )
    name = models.CharField(max_length=150, verbose_name=_('nombre'))
    market_type = models.CharField(max_length=20, choices=Type.choices, verbose_name=_('tipo'))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ABIERTO,
        verbose_name=_('estado'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('creado en'))

    class Meta:
        verbose_name = _('mercado')
        verbose_name_plural = _('mercados')
        indexes = [
            models.Index(fields=['event', 'status'], name='idx_market_event_status'),
        ]

    def __str__(self):
        return f'{self.event.name} - {self.name}'


class Selection(models.Model):
    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        related_name='selections',
        verbose_name=_('mercado'),
    )
    name = models.CharField(max_length=100, verbose_name=_('nombre'))
    odds = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=settings.DECIMAL_PLACES,
        verbose_name=_('cuota'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('creado en'))

    class Meta:
        verbose_name = _('seleccion')
        verbose_name_plural = _('selecciones')
        constraints = [
            models.UniqueConstraint(fields=['market', 'name'], name='unique_selection_per_market'),
        ]

    def __str__(self):
        return f'{self.name} @ {self.odds}'


class Bet(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='bets',
        verbose_name=_('usuario'),
    )
    market = models.ForeignKey(
        Market,
        on_delete=models.PROTECT,
        related_name='bets',
        verbose_name=_('mercado'),
    )
    selection = models.ForeignKey(
        Selection,
        on_delete=models.PROTECT,
        related_name='bets',
        verbose_name=_('seleccion'),
    )
    stake = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=settings.DECIMAL_PLACES,
        verbose_name=_('monto apostado'),
    )
    odds = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=settings.DECIMAL_PLACES,
        verbose_name=_('cuota aceptada'),
    )
    status = models.CharField(
        max_length=20,
        choices=BetStatus.choices,
        default=BetStatus.ACCEPTED,
        verbose_name=_('estado'),
    )
    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('creado en'))

    class Meta:
        verbose_name = _('apuesta')
        verbose_name_plural = _('apuestas')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status'], name='idx_bet_user_status'),
            models.Index(fields=['market', 'status'], name='idx_bet_market_status'),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status = self.status

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._original_status = instance.status
        return instance

    @property
    def is_settled(self):
        return self.status in {
            BetStatus.SETTLED_WON,
            BetStatus.SETTLED_LOST,
            BetStatus.CANCELLED,
        }

    def clean(self):
        super().clean()
        if self.selection_id and self.market_id and self.selection.market_id != self.market_id:
            raise ValidationError({'selection': 'La seleccion no pertenece al mercado indicado.'})

        if self.pk and self.status != self._original_status:
            if self._original_status != BetStatus.ACCEPTED:
                raise ValidationError({'status': 'No se puede cambiar una apuesta liquidada.'})
            if not can_transition(self._original_status, self.status):
                raise ValidationError({'status': 'Transicion de estado invalida.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self._original_status = self.status

    def __str__(self):
        return f'{self.user.email} - {self.selection.name} ({self.stake})'
