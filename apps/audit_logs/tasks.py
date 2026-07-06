from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

from .models import AuditLog

logger = logging.getLogger(__name__)

@shared_task
def cleanup_old_audit_logs():
    """
    Periodic task to clean up audit logs older than the configured retention period.
    """
    retention_days = getattr(settings, 'AUDIT_LOG_RETENTION_DAYS', 30)
    cutoff_date = timezone.now() - timedelta(days=retention_days)
    
    logger.info(f"Starting audit log cleanup. Retention days: {retention_days}. Deleting logs older than {cutoff_date}.")
    
    # Use bulk delete for efficiency
    deleted_count, _ = AuditLog.objects.filter(timestamp__lt=cutoff_date).delete()
    
    logger.info(f"Audit log cleanup completed. Deleted {deleted_count} old logs.")
    return deleted_count
