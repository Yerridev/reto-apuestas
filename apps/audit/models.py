import hashlib
import json

from django.db import models, transaction


def compute_hash(prev_hash, payload):
    """
    Calcula el hash SHA256 de un registro enlazando el hash previo
    con el payload serializado en orden estable.
    """
    raw = (prev_hash + json.dumps(payload, sort_keys=True)).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


class AuditLog(models.Model):
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    prev_hash = models.CharField(max_length=64)
    hash = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'registro de auditoria'
        verbose_name_plural = 'registros de auditoria'

    def save(self, *args, **kwargs):
        """
        Al crear un registro nuevo, resuelve el hash anterior y calcula
        el hash actual antes de persistirlo en la cadena.
        """
        if self._state.adding and (not self.prev_hash or not self.hash):
            with transaction.atomic():
                previous = AuditLog.objects.select_for_update().order_by('-created_at', '-id').first()
                self.prev_hash = previous.hash if previous else '0'
                self.hash = compute_hash(self.prev_hash, self.payload)
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.event_type} @ {self.created_at}'
