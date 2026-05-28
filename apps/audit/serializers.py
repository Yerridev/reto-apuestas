from rest_framework import serializers

from apps.audit.models import SuspiciousActivity


class SuspiciousActivitySerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = SuspiciousActivity
        fields = ['id', 'user_email', 'rule_triggered', 'detail', 'reviewed', 'created_at']
