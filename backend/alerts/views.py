from django.utils import timezone
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Alert
from .serializers import AlertSerializer


class AlertViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    The signed-in user's alerts, newest first. `unread-count/` feeds the badge in the header menu;
    `read-all/` marks everything read (the Alerts page calls it once it has shown them) and `<id>/read/`
    marks one.
    """
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Alert.objects.filter(account=self.request.user)

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        return Response({'count': self.get_queryset().filter(read_at__isnull=True).count()})

    @action(detail=False, methods=['post'], url_path='read-all')
    def read_all(self, request):
        updated = self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({'marked_read': updated})

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        alert = self.get_object()
        if alert.read_at is None:
            alert.read_at = timezone.now()
            alert.save(update_fields=['read_at'])
        return Response(self.get_serializer(alert).data)
