from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Full queryset — all notifications for the current user."""
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """
        Override the default list action so the /feed/ endpoint returns
        only the latest 5 **unread** notifications for the notification panel.
        """
        unread_qs = (
            Notification.objects
            .filter(recipient=request.user, is_read=False)
            .order_by('-created_at')[:5]
        )
        serializer = self.get_serializer(unread_qs, many=True)
        unread_count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return Response({
            'unread_count': unread_count,
            'results': serializer.data,
        })

    @action(detail=False, methods=['GET'], url_path='all')
    def all_notifications(self, request):
        """Return full notification history (all, read + unread)."""
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['POST'], url_path='mark-all-read')
    def mark_all_read(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read.'})

    @action(detail=True, methods=['POST'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read.'})
