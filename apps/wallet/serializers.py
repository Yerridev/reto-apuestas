from decimal import Decimal

from rest_framework import serializers

from apps.users.choices import AccountStatus


class DepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal('0.0001'))
    idempotency_key = serializers.UUIDField(required=False, default=None)

    def validate(self, data):
        user = self.context['request'].user

        if user.account_status != AccountStatus.VERIFICADO:
            raise serializers.ValidationError(
                'Tu cuenta debe estar verificada para realizar depósitos.'
            )

        limit_map = {
            'deposit_limit_daily': 'diario',
            'deposit_limit_weekly': 'semanal',
            'deposit_limit_monthly': 'mensual',
        }
        for field, label in limit_map.items():
            limit = getattr(user, field)
            if limit is not None and data['amount'] > limit:
                raise serializers.ValidationError(
                    f'El monto supera tu límite {label} de depósito ({limit}).'
                )

        return data


class BalanceSerializer(serializers.Serializer):
    balance = serializers.DecimalField(max_digits=18, decimal_places=4)
    currency = serializers.CharField(default='fichas')
