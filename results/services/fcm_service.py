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
    
    @staticmethod
    def send_to_token(token: str, title: str, body: str, data: Dict = None, image_url: str = None) -> bool:
        """
        Send notification to a single FCM token
        
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
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            
            # Build Android specific config
            android_config = messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    icon='ic_notification',  # Your app's notification icon
                    color='#FF6B35',  # Your app's primary color
                    sound='default',
                    click_action='FLUTTER_NOTIFICATION_CLICK'
                )
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
            
        except Exception as e:
            logger.error(f"❌ Failed to send notification to token {token[:10]}...: {e}")
            return False
    
    @staticmethod
    def send_to_multiple_tokens(tokens: List[str], title: str, body: str, data: Dict = None, image_url: str = None) -> Dict:
        """
        Send notification to multiple FCM tokens
        
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
            # Remove empty or None tokens
            valid_tokens = [token for token in tokens if token and token.strip()]
            
            if not valid_tokens:
                return {'success_count': 0, 'failure_count': 0, 'invalid_tokens': tokens}
            
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            
            # Build Android specific config
            android_config = messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    icon='ic_notification',
                    color='#FF6B35',
                    sound='default',
                    click_action='FLUTTER_NOTIFICATION_CLICK'
                )
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
            
            # Handle invalid tokens
            invalid_tokens = []
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        invalid_tokens.append(valid_tokens[idx])
                        logger.warning(f"❌ Failed to send to token {valid_tokens[idx][:10]}...: {resp.exception}")
            
            logger.info(f"✅ Multicast complete: {response.success_count} successful, {response.failure_count} failed")
            
            return {
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'invalid_tokens': invalid_tokens
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
            
            # Send to all tokens
            result = FCMService.send_to_multiple_tokens(tokens, title, body, data, image_url)
            
            # Clean up invalid tokens
            if result['invalid_tokens']:
                User.objects.filter(fcm_token__in=result['invalid_tokens']).update(fcm_token=None)
                logger.info(f"🧹 Cleaned up {len(result['invalid_tokens'])} invalid tokens")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to send notification to all users: {e}")
            return {'success_count': 0, 'failure_count': 0, 'invalid_tokens': []}
    
    # Replace these two methods in your existing fcm_service.py

    @staticmethod
    def send_lottery_result_started(lottery_name: str) -> Dict:
        """
        Send notification when lottery result addition starts
        Frontend expects type: 'live_result_starts'
        """
        title = "Live Results Starting!"
        body = f"Kerala {lottery_name} lottery results are now loading. Stay tuned!"
        
        data = {
            'type': 'live_result_starts',  # Changed from 'result_started' to match frontend
            'lottery_name': lottery_name,
            'timestamp': str(int(datetime.now().timestamp()))  # Changed to epoch timestamp
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
            'type': 'result_published',  # Changed from 'result_completed' to match frontend
            'result_id': result_unique_id or '',  # Added result_id field for navigation
            'lottery_name': lottery_name,
            'draw_number': draw_number,
            'timestamp': str(int(datetime.now().timestamp()))  # Changed to epoch timestamp
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
            'timestamp': datetime.now().isoformat()
        }
        
        return FCMService.send_to_all_users(title, body, data)