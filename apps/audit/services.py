from apps.audit.models import AuditLog, compute_hash


def verify_chain():
    """
    Recorre toda la cadena de auditoria en orden cronologico y valida
    que cada registro apunte correctamente al hash anterior.
    """
    previous_hash = '0'

    for index, record in enumerate(AuditLog.objects.order_by('created_at', 'id'), start=1):
        expected_hash = compute_hash(previous_hash, record.payload)
        if record.prev_hash != previous_hash or record.hash != expected_hash:
            return {
                'valid': False,
                'broken_at': index,
                'expected_hash': expected_hash,
                'found_hash': record.hash,
            }
        previous_hash = record.hash

    return {
        'valid': True,
        'total_records': AuditLog.objects.count(),
    }
