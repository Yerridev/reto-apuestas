from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from apps.users.choices import AccountStatus
from apps.users.models import DepositLimitChange, SelfExclusion, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'email', 'dni', 'get_full_name', 'account_status',
        'is_staff', 'date_joined',
    ]
    list_filter = ['account_status', 'is_staff', 'is_superuser']
    search_fields = ['email', 'dni', 'first_name', 'last_name']
    ordering = ['-date_joined']

    fieldsets = [
        (
            _('Credenciales'),
            {'fields': ['email', 'password']},
        ),
        (
            _('Datos personales'),
            {'fields': ['dni', 'first_name', 'last_name', 'birth_date']},
        ),
        (
            _('Estado de cuenta'),
            {'fields': ['account_status']},
        ),
        (
            _('Límites de juego responsable'),
            {
                'fields': [
                    'deposit_limit_daily',
                    'deposit_limit_weekly',
                    'deposit_limit_monthly',
                    'deposit_limit_updated_at',
                ],
            },
        ),
        (
            _('Permisos'),
            {
                'fields': [
                    'is_active', 'is_staff', 'is_superuser',
                    'groups', 'user_permissions',
                ],
            },
        ),
        (
            _('Fechas'),
            {'fields': ['last_login', 'date_joined']},
        ),
    ]

    add_fieldsets = [
        (
            None,
            {
                'classes': ['wide'],
                'fields': [
                    'email', 'dni', 'first_name', 'last_name',
                    'birth_date', 'password1', 'password2',
                ],
            },
        ),
    ]


@admin.register(SelfExclusion)
class SelfExclusionAdmin(admin.ModelAdmin):
    list_display = ['user', 'exclusion_type', 'start_date', 'end_date']
    list_filter = ['exclusion_type']
    search_fields = ['user__email', 'user__dni']


@admin.register(DepositLimitChange)
class DepositLimitChangeAdmin(admin.ModelAdmin):
    list_display = ['user', 'field_name', 'old_value', 'new_value', 'created_at']
    list_filter = ['field_name']
    search_fields = ['user__email', 'user__dni']
    readonly_fields = ['user', 'field_name', 'old_value', 'new_value', 'created_at']
