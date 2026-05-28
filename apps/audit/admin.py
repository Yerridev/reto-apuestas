from django.contrib import admin

from apps.audit.models import AuditLog, SuspiciousActivity


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'created_at', 'hash')
    search_fields = ('event_type', 'hash')
    readonly_fields = ('event_type', 'payload', 'prev_hash', 'hash', 'created_at')


@admin.register(SuspiciousActivity)
class SuspiciousActivityAdmin(admin.ModelAdmin):
    list_display = ('rule_triggered', 'user', 'reviewed', 'created_at')
    list_filter = ('rule_triggered', 'reviewed', 'created_at')
    search_fields = ('user__email', 'rule_triggered')
