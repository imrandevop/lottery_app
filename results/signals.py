from django.db.models.signals import post_save
from django.dispatch import receiver
from results.models import LotteryResult
from results.utils.cache_utils import invalidate_prediction_cache
import logging

logger = logging.getLogger('lottery_app')

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