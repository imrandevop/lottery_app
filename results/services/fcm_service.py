# results/services/fcm_service.py

import logging
from typing import List, Dict, Optional
from firebase_admin import messaging
from django.conf import settings
from django.contrib.auth import get_user_model
from datetime import datetime

logger = logging.getLogger('lottery_app')
User = get_user_model()

class FCMService:
    """
    Firebase Cloud Messaging service for sending push notifications
    """
    
    # Replace the validate_fcm_token method in fcm_service.py with this improved version

    # Temporarily replace the validate_fcm_token method with this:

    @staticmethod
    def validate_fcm_token(token: str) -> bool:
        """
        TEMPORARY: Disable validation to test notifications
        """
        # Basic checks only
        if not token or not isinstance(token, str):
            return False
        
        token = token.strip()
        
        # Very basic length check
        if len(token) < 50:
            return False
        
        # For now, return True for all tokens that pass basic checks
        return True
        
        # TODO: Re-enable proper validation after testing
        # Original validation code below...
    
    @staticmethod
    def send_to_token(token: str, title: str, body: str, data: Dict = None, image_url: str = None) -> bool:
        """
        Enhanced send_to_token with validation
        
        Args:
            token: FCM token
            title: Notification title
            body: Notification body
            data: Additional data (optional)
            image_url: Image URL for rich notifications (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate token first
            if not FCMService.validate_fcm_token(token):
                logger.error(f"❌ Invalid FCM token format: {token[:10]}...")
                return False
            
            # Build notification with proper Android configuration
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            
            # Enhanced Android config
            android_config = messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    icon='ic_notification',
                    color='#FF6B35',
                    sound='default',
                    click_action='FLUTTER_NOTIFICATION_CLICK',
                    channel_id='default_channel',  # Add channel ID
                    tag='lottery_notification'  # Add tag for grouping
                ),
                data=data or {}
            )
            
            # Build message
            message = messaging.Message(
                notification=notification,
                token=token,
                data=data or {},
                android=android_config
            )
            
            # Send message
            response = messaging.send(message)
            logger.info(f"✅ Notification sent successfully: {response}")
            return True
            
        except messaging.UnregisteredError:
            logger.error(f"❌ FCM token is unregistered: {token[:10]}...")
            # Auto-cleanup invalid token
            User.objects.filter(fcm_token=token).update(fcm_token=None)
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to send notification to token {token[:10]}...: {e}")
            return False
    
    @staticmethod
    def send_to_multiple_tokens(tokens: List[str], title: str, body: str, data: Dict = None, image_url: str = None) -> Dict:
        """
        Send notification to multiple FCM tokens with enhanced validation
        
        Args:
            tokens: List of FCM tokens
            title: Notification title
            body: Notification body
            data: Additional data (optional)
            image_url: Image URL for rich notifications (optional)
            
        Returns:
            Dict: Success and failure counts
        """
        if not tokens:
            return {'success_count': 0, 'failure_count': 0, 'invalid_tokens': []}
        
        try:
            # Validate and filter tokens
            valid_tokens = []
            invalid_tokens = []
            
            for token in tokens:
                if token and token.strip() and FCMService.validate_fcm_token(token):
                    valid_tokens.append(token)
                else:
                    invalid_tokens.append(token)
            
            if not valid_tokens:
                logger.warning(f"⚠️ No valid tokens found out of {len(tokens)} provided")
                return {'success_count': 0, 'failure_count': len(tokens), 'invalid_tokens': tokens}
            
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            
            # Enhanced Android config
            android_config = messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    icon='ic_notification',
                    color='#FF6B35',
                    sound='default',
                    click_action='FLUTTER_NOTIFICATION_CLICK',
                    channel_id='default_channel',
                    tag='lottery_notification'
                ),
                data=data or {}
            )
            
            # Build multicast message
            message = messaging.MulticastMessage(
                notification=notification,
                tokens=valid_tokens,
                data=data or {},
                android=android_config
            )
            
            # Send message
            response = messaging.send_multicast(message)
            
            # Handle failed responses
            failed_tokens = []
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        failed_token = valid_tokens[idx]
                        failed_tokens.append(failed_token)
                        logger.warning(f"❌ Failed to send to token {failed_token[:10]}...: {resp.exception}")
                        
                        # Auto-cleanup unregistered tokens
                        if isinstance(resp.exception, messaging.UnregisteredError):
                            User.objects.filter(fcm_token=failed_token).update(fcm_token=None)
                            logger.info(f"🧹 Cleaned up unregistered token: {failed_token[:10]}...")
            
            # Combine all invalid tokens
            all_invalid_tokens = invalid_tokens + failed_tokens
            
            logger.info(f"✅ Multicast complete: {response.success_count} successful, {response.failure_count} failed, {len(invalid_tokens)} invalid format")
            
            return {
                'success_count': response.success_count,
                'failure_count': response.failure_count + len(invalid_tokens),
                'invalid_tokens': all_invalid_tokens
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to send multicast notification: {e}")
            return {'success_count': 0, 'failure_count': len(tokens), 'invalid_tokens': tokens}
    
    @staticmethod
    def send_to_all_users(title: str, body: str, data: Dict = None, image_url: str = None) -> Dict:
        """
        Send notification to all users with FCM tokens
        
        Args:
            title: Notification title
            body: Notification body
            data: Additional data (optional)
            image_url: Image URL for rich notifications (optional)
            
        Returns:
            Dict: Success and failure counts
        """
        try:
            # Get all valid FCM tokens
            users_with_tokens = User.objects.filter(
                fcm_token__isnull=False,
                notifications_enabled=True
            ).exclude(fcm_token='').values_list('fcm_token', flat=True)
            
            tokens = list(users_with_tokens)
            
            if not tokens:
                logger.warning("⚠️ No FCM tokens found for users")
                return {'success_count': 0, 'failure_count': 0, 'invalid_tokens': []}
            
            logger.info(f"📱 Sending notification to {len(tokens)} users")
            
            # Send to all tokens with enhanced validation
            result = FCMService.send_to_multiple_tokens(tokens, title, body, data, image_url)
            
            # Clean up invalid tokens from database
            if result['invalid_tokens']:
                User.objects.filter(fcm_token__in=result['invalid_tokens']).update(fcm_token=None)
                logger.info(f"🧹 Cleaned up {len(result['invalid_tokens'])} invalid tokens from database")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to send notification to all users: {e}")
            return {'success_count': 0, 'failure_count': 0, 'invalid_tokens': []}
    
    @staticmethod
    def send_lottery_result_started(lottery_name: str) -> Dict:
        """
        Send notification when lottery result addition starts
        Frontend expects type: 'live_result_starts'
        """
        title = "Live Results Starting!"
        body = f"Kerala {lottery_name} lottery results are now loading. Stay tuned!"
        
        data = {
            'type': 'live_result_starts',
            'lottery_name': lottery_name,
            'timestamp': str(int(datetime.now().timestamp()))
        }
        
        return FCMService.send_to_all_users(title, body, data)

    @staticmethod
    def send_lottery_result_completed(lottery_name: str, draw_number: str, result_unique_id: str = None) -> Dict:
        """
        Send notification when lottery result addition is completed
        Frontend expects type: 'result_published'
        """
        title = "Results Published!"
        body = f"{lottery_name} Draw {draw_number} results are now available. Check if you won!"
        
        data = {
            'type': 'result_published',
            'result_id': result_unique_id or '',
            'lottery_name': lottery_name,
            'draw_number': draw_number,
            'timestamp': str(int(datetime.now().timestamp()))
        }
        
        return FCMService.send_to_all_users(title, body, data)
    
    @staticmethod
    def test_notification() -> Dict:
        """
        Send a test notification to all users
        """
        title = "🧪 Test Notification"
        body = "This is a test notification from Kerala Lottery App!"
        
        data = {
            'type': 'test',
            'timestamp': str(int(datetime.now().timestamp()))
        }
        
        result = FCMService.send_to_all_users(title, body, data)
        
        # Additional debugging info
        logger.info(f"📊 Test notification result: {result}")
        
        return result
    
    @staticmethod
    def get_user_token_stats() -> Dict:
        """
        Get statistics about user FCM tokens for debugging
        """
        try:
            total_users = User.objects.count()
            users_with_tokens = User.objects.filter(
                fcm_token__isnull=False
            ).exclude(fcm_token='').count()
            
            users_with_notifications_enabled = User.objects.filter(
                fcm_token__isnull=False,
                notifications_enabled=True
            ).exclude(fcm_token='').count()
            
            stats = {
                'total_users': total_users,
                'users_with_tokens': users_with_tokens,
                'users_with_notifications_enabled': users_with_notifications_enabled,
                'token_coverage_percentage': round((users_with_tokens / total_users * 100), 2) if total_users > 0 else 0,
                'notification_enabled_percentage': round((users_with_notifications_enabled / total_users * 100), 2) if total_users > 0 else 0
            }
            
            logger.info(f"📊 FCM Token Stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get token stats: {e}")
            return {
                'total_users': 0,
                'users_with_tokens': 0,
                'users_with_notifications_enabled': 0,
                'token_coverage_percentage': 0,
                'notification_enabled_percentage': 0,
                'error': str(e)
            }