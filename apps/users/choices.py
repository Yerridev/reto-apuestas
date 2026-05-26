from django.db import models


class AccountStatus(models.TextChoices):
    PENDIENTE_VERIFICACION = 'pendiente_verificacion', 'Pendiente de verificación'
    VERIFICADO = 'verificado', 'Verificado'
    BLOQUEADO = 'bloqueado', 'Bloqueado'
    AUTOEXCLUIDO = 'autoexcluido', 'Autoexcluido'


class ExclusionType(models.TextChoices):
    TEMPORAL_7 = '7_dias', '7 días'
    TEMPORAL_30 = '30_dias', '30 días'
    TEMPORAL_90 = '90_dias', '90 días'
    INDEFINIDA = 'indefinida', 'Indefinida'
