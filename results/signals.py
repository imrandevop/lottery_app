from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from results.models import LotteryResult
from results.utils.cache_utils import invalidate_prediction_cache
import logging
logger = logging.getLogger('lottery_app')
from .models import LotteryResult
from .services.fcm_service import FCMService


@receiver(post_save, sender=LotteryResult)
def invalidate_cache_on_new_result(sender, instance, created, **kwargs):
    """
    Invalidate prediction cache when new lottery result is published
    """
    if instance.is_published:
        try:
            lottery_name = instance.lottery.name
            invalidate_prediction_cache(lottery_name)
            logger.info(f"Cache invalidated for new result: {lottery_name}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")



#<---------------------NOTIFICATIONS SECTION--------------------->

# results/signals.py - Create this new file



# 2. Create results/signals.py

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import LotteryResult
from .services.fcm_service import FCMService

logger = logging.getLogger('lottery_app')

@receiver(post_save, sender=LotteryResult)
def handle_lottery_result_notifications(sender, instance, created, **kwargs):
    """Handle notifications for lottery results"""
    
    # 1. Send notification when NEW result is created with is_published=True
    if created and instance.is_published:
        try:
            result = FCMService.send_new_result_notification(instance.lottery.name)
            logger.info(f"📱 New result notification triggered for {instance.lottery.name}: {result['message']}")
            print(f"📱 NEW RESULT NOTIFICATION: {instance.lottery.name}")
        except Exception as e:
            logger.error(f"❌ Failed to send new result notification: {e}")
    
    # 2. Send notification when results_ready_notification is checked and saved
    elif not created and instance.results_ready_notification and not instance.notification_sent:
        try:
            result = FCMService.send_result_ready_notification(
                instance.lottery.name, 
                instance.draw_number
            )
            
            # Mark notification as sent to prevent duplicate sends
            instance.notification_sent = True
            instance.save(update_fields=['notification_sent'])
            
            logger.info(f"📱 Result ready notification triggered for {instance.lottery.name} - {instance.draw_number}: {result['message']}")
            print(f"📱 RESULT READY NOTIFICATION: {instance.lottery.name} - {instance.draw_number}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send result ready notification: {e}")

