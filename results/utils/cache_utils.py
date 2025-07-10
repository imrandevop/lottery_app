import logging
from django.core.cache import cache
import hashlib
from typing import Any, Optional

logger = logging.getLogger('lottery_app')

def make_cache_key(*args) -> str:
    """Create a consistent cache key"""
    key_string = "_".join(str(arg) for arg in args)
    if len(key_string) > 200:
        key_string = hashlib.md5(key_string.encode()).hexdigest()
    return f"lottery_{key_string}"

def cache_prediction(lottery_name: str, prize_type: str, prediction_data: dict, timeout: int = 3600) -> bool:
    """Cache prediction with error handling"""
    try:
        cache_key = make_cache_key("prediction", lottery_name.lower(), prize_type)
        cache.set(cache_key, prediction_data, timeout)
        logger.info(f"Cached prediction: {lottery_name}-{prize_type}")
        return True
    except Exception as e:
        logger.info(f"Cache unavailable: {e}")
        return False

def get_cached_prediction(lottery_name: str, prize_type: str) -> Optional[dict]:
    """Get cached prediction with error handling"""
    try:
        cache_key = make_cache_key("prediction", lottery_name.lower(), prize_type)
        data = cache.get(cache_key)
        if data:
            logger.info(f"Cache HIT: {lottery_name}-{prize_type}")
        return data
    except Exception as e:
        logger.info(f"Cache read failed: {e}")
        return None

def cache_historical_data(lottery_name: str, prize_type: str, data: list, timeout: int = 1800) -> bool:
    """Cache historical data"""
    try:
        cache_key = make_cache_key("historical", lottery_name.lower(), prize_type)
        cache.set(cache_key, data, timeout)
        return True
    except Exception:
        return False

def get_cached_historical_data(lottery_name: str, prize_type: str) -> Optional[list]:
    """Get cached historical data"""
    try:
        cache_key = make_cache_key("historical", lottery_name.lower(), prize_type)
        return cache.get(cache_key)
    except Exception:
        return None

def invalidate_prediction_cache(lottery_name: str, prize_type: Optional[str] = None) -> bool:
    """Invalidate prediction cache"""
    try:
        if prize_type:
            cache_key = make_cache_key("prediction", lottery_name.lower(), prize_type)
            cache.delete(cache_key)
        else:
            prize_types = ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th']
            for pt in prize_types:
                cache_key = make_cache_key("prediction", lottery_name.lower(), pt)
                cache.delete(cache_key)
        return True
    except Exception:
        return False