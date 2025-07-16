from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from results.models import LotteryResult
from results.utils.cache_utils import invalidate_prediction_cache
import logging
logger = logging.getLogger('lottery_app')
from .models import LotteryResult, NotificationLog
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



@receiver(pre_save, sender=LotteryResult)
def lottery_result_pre_save(sender, instance, **kwargs):
    """
    Track when a lottery result is first created (started)
    """
    if instance.pk is None:  # New instance being created
        # Store flag to send notification after save
        instance._send_started_notification = True

@receiver(post_save, sender=LotteryResult)
def lottery_result_post_save(sender, instance, created, **kwargs):
    """
    Send notifications based on lottery result status
    """
    try:
        # Send "started" notification when result is first created
        if created and getattr(instance, '_send_started_notification', False):
            logger.info(f"📱 Sending 'started' notification for {instance.lottery.name}")
            
            result = FCMService.send_lottery_result_started(instance.lottery.name)
            
            # Log the notification
            NotificationLog.objects.create(
                notification_type='result_started',
                title="🎯 Kerala Lottery Results Loading...",
                body=f"We're adding the latest {instance.lottery.name} results. Stay tuned!",
                lottery_name=instance.lottery.name,
                draw_number=instance.draw_number,
                success_count=result['success_count'],
                failure_count=result['failure_count'],
                total_tokens=result['success_count'] + result['failure_count']
            )
        
        # Send "completed" notification when result is published
        if instance.is_published:
            # Check if this is the first time being published
            if created or (hasattr(instance, '_state') and 'is_published' in instance._state.fields_cache):
                # Get previous state
                try:
                    if not created:
                        old_instance = LotteryResult.objects.get(pk=instance.pk)
                        was_published = old_instance.is_published
                    else:
                        was_published = False
                    
                    # Only send if newly published
                    if not was_published and instance.is_published:
                        logger.info(f"📱 Sending 'completed' notification for {instance.lottery.name}")
                        
                        result = FCMService.send_lottery_result_completed(
                            instance.lottery.name, 
                            instance.draw_number
                        )
                        
                        # Log the notification
                        NotificationLog.objects.create(
                            notification_type='result_completed',
                            title="🎉 Kerala Lottery Results Ready!",
                            body=f"{instance.lottery.name} Draw {instance.draw_number} results are now available. Check if you won!",
                            lottery_name=instance.lottery.name,
                            draw_number=instance.draw_number,
                            success_count=result['success_count'],
                            failure_count=result['failure_count'],
                            total_tokens=result['success_count'] + result['failure_count']
                        )
                        
                except Exception as e:
                    logger.error(f"❌ Error checking previous publish state: {e}")
    
    except Exception as e:
        logger.error(f"❌ Error in lottery result signal: {e}")