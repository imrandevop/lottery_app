from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.cache import cache
import logging

logger = logging.getLogger('lottery_app')
User = get_user_model()

@receiver(post_save, sender=User)
def user_created_signal(sender, instance, created, **kwargs):
    """
    Signal fired when a user is created or updated
    """
    if created:
        # Get current count
        current_count = User.objects.count()
        
        # Cache the count for performance
        cache.set('user_count', current_count, timeout=300)  # 5 minutes
        
        logger.info(f"New user created: {instance.name} ({instance.phone_number}). Total users: {current_count}")
        
        # You could add WebSocket notification here if needed
        # websocket_notify_user_count_change(current_count)

@receiver(post_delete, sender=User)
def user_deleted_signal(sender, instance, **kwargs):
    """
    Signal fired when a user is deleted
    """
    # Get current count
    current_count = User.objects.count()
    
    # Cache the count for performance
    cache.set('user_count', current_count, timeout=300)  # 5 minutes
    
    logger.info(f"User deleted: {instance.name} ({instance.phone_number}). Total users: {current_count}")
    
    # You could add WebSocket notification here if needed
    # websocket_notify_user_count_change(current_count)

def get_user_count():
    """
    Get user count from cache or database
    """
    count = cache.get('user_count')
    if count is None:
        count = User.objects.count()
        cache.set('user_count', count, timeout=300)  # 5 minutes
    return count