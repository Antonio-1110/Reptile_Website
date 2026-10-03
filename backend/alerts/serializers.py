from rest_framework import serializers

from .models import Alert
from .services import text_for


class AlertSerializer(serializers.ModelSerializer):
    """An alert in the reader's language (from Accept-Language)."""
    title = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = ['id', 'title', 'body', 'link', 'created_at', 'is_read']

    def get_title(self, alert):
        return text_for(alert)[0]

    def get_body(self, alert):
        return text_for(alert)[1]

    def get_is_read(self, alert):
        return alert.read_at is not None
