import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import LotteryResult
from .services.fcm_service import FCMService

logger = logging.getLogger('lottery_app')

# Single consolidated signal handler for all LotteryResult operations
@receiver(pre_save, sender=LotteryResult)
def lottery_result_pre_save_handler(sender, instance, **kwargs):
    """
    Store the original state before save to detect changes
    """
    if instance.pk:
        try:
            old_instance = LotteryResult.objects.get(pk=instance.pk)
            instance._original_published = old_instance.is_published
            instance._original_results_ready = old_instance.results_ready_notification
            instance._original_notification_sent = old_instance.notification_sent
        except LotteryResult.DoesNotExist:
            instance._original_published = False
            instance._original_results_ready = False
            instance._original_notification_sent = False
    else:
        instance._original_published = False
        instance._original_results_ready = False
        instance._original_notification_sent = False

@receiver(post_save, sender=LotteryResult)
def lottery_result_post_save_handler(sender, instance, created, **kwargs):
    """
    Consolidated handler for all LotteryResult post-save operations
    """
    try:
        # 1. Cache invalidation
        if instance.is_published:
            try:
                from results.utils.cache_utils import invalidate_prediction_cache
                lottery_name = instance.lottery.name
                invalidate_prediction_cache(lottery_name)
                logger.info(f"Cache invalidated for result: {lottery_name}")
            except Exception as e:
                logger.error(f"Failed to invalidate cache: {e}")

        # 2. Handle notifications
        if created:
            # New result created - send notification only if published
            if instance.is_published:
                logger.info(f"📱 New lottery result created and published: {instance.lottery.name}")
                try:
                    result = FCMService.send_new_result_notification(instance.lottery.name)
                    logger.info(f"📤 New result notification sent: {result}")
                except Exception as e:
                    logger.error(f"❌ Failed to send new result notification: {e}")
        else:
            # Existing result updated

            # Check if is_published changed from False to True
            if (hasattr(instance, '_original_published') and
                not instance._original_published and
                instance.is_published):

                logger.info(f"📱 Lottery result published (False→True): {instance.lottery.name}")
                try:
                    result = FCMService.send_new_result_notification(instance.lottery.name)
                    logger.info(f"📤 Publication notification sent: {result}")
                except Exception as e:
                    logger.error(f"❌ Failed to send publication notification: {e}")

            # Check if results_ready_notification was just checked
            if (hasattr(instance, '_original_results_ready') and
                hasattr(instance, '_original_notification_sent') and
                not instance._original_results_ready and
                instance.results_ready_notification and
                not instance._original_notification_sent and
                not instance.notification_sent):

                logger.info(f"📱 Result ready notification triggered: {instance.lottery.name}")
                try:
                    result = FCMService.send_result_ready_notification(
                        instance.lottery.name,
                        instance.draw_number
                    )

                    # CRITICAL FIX: Use update() to avoid triggering signals again
                    LotteryResult.objects.filter(pk=instance.pk).update(notification_sent=True)

                    logger.info(f"📤 Result ready notification sent: {result}")

                except Exception as e:
                    logger.error(f"❌ Failed to send result ready notification: {e}")

    except Exception as e:
        logger.error(f"❌ Error in lottery_result_post_save_handler: {e}")
        import traceback
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")

