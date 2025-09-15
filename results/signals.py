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
                logger.info(f"New lottery result created and published: {instance.lottery.name}")

                # PERFORMANCE FIX: Send asynchronously
                import threading

                def send_new_result_async():
                    try:
                        result = FCMService.send_new_result_notification(instance.lottery.name)
                        logger.info(f"Background new result notification sent: {result}")
                    except Exception as e:
                        logger.error(f"Background new result notification failed: {e}")

                threading.Thread(
                    target=send_new_result_async,
                    name=f"NewResultThread-{instance.lottery.name}",
                    daemon=True
                ).start()

                logger.info(f"New result notification queued in background")
        else:
            # Existing result updated

            # Check if is_published changed from False to True



            if (hasattr(instance, '_original_published') and
                not instance._original_published and
                instance.is_published):

                logger.info(f"Lottery result published (False→True): {instance.lottery.name}")

                # PERFORMANCE FIX: Send asynchronously
                import threading

                def send_publication_async():
                    try:
                        result = FCMService.send_new_result_notification(instance.lottery.name)
                        logger.info(f"Background publication notification sent: {result}")
                    except Exception as e:
                        logger.error(f"Background publication notification failed: {e}")

                threading.Thread(
                    target=send_publication_async,
                    name=f"PublicationThread-{instance.lottery.name}",
                    daemon=True
                ).start()

                logger.info(f"Publication notification queued in background")

            # Check if results_ready_notification was just checked
            # Simplified logic: send notification if checkbox is checked and not already sent
            if (instance.results_ready_notification and
                not instance.notification_sent and
                instance.is_published):

                # For existing records, only send if this is a new request
                should_send = True
                if hasattr(instance, '_original_results_ready'):
                    # If notification was already requested before, don't send again
                    if instance._original_results_ready and getattr(instance, '_original_notification_sent', False):
                        should_send = False

                if should_send:
                    logger.info(f"Result ready notification triggered: {instance.lottery.name}")

                    # PERFORMANCE FIX: Send notifications asynchronously in background
                    # This makes admin interface respond immediately
                    import threading

                    def send_notification_async():
                        """Background thread function for sending notifications"""
                        try:
                            logger.info(f"Starting background notification for: {instance.lottery.name}")

                            result = FCMService.send_result_ready_notification(
                                instance.lottery.name,
                                instance.draw_number
                            )

                            # Mark as sent after successful delivery
                            LotteryResult.objects.filter(pk=instance.pk).update(notification_sent=True)

                            logger.info(f"Background notification completed: {result}")

                        except Exception as e:
                            logger.error(f"Background notification failed: {e}")
                            # Don't mark as sent if failed, so admin can retry

                    # Start background thread (non-blocking)
                    notification_thread = threading.Thread(
                        target=send_notification_async,
                        name=f"NotificationThread-{instance.lottery.name}-{instance.pk}",
                        daemon=True  # Thread dies when main process exits
                    )
                    notification_thread.start()

                    logger.info(f"Notification queued in background for: {instance.lottery.name}")
                # Admin interface returns immediately here!

    except Exception as e:
        logger.error(f"Error in lottery_result_post_save_handler: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

