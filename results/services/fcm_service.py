# Replace your results/services/fcm_service.py with this production-ready version:

import logging
from typing import List, Dict
from django.conf import settings
from django.utils import timezone
from firebase_admin import credentials, messaging, initialize_app
import firebase_admin
from results.models import FcmToken

logger = logging.getLogger('lottery_app')

class FCMService:
    """Production-ready Firebase FCM service"""
    
    _initialized = False
    _test_mode = False
    
    @classmethod
    def _initialize_firebase(cls):
        """Initialize Firebase Admin SDK for production"""
        if not cls._initialized:
            try:
                if not firebase_admin._apps:
                    # Try to get credentials
                    if hasattr(settings, 'FIREBASE_CREDENTIALS_FILE'):
                        # Development: Use service account file
                        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_FILE)
                        initialize_app(cred)
                        logger.info("✅ Firebase initialized with service account file")
                    elif hasattr(settings, 'FIREBASE_CREDENTIALS') and settings.FIREBASE_CREDENTIALS:
                        # Production: Use environment variables
                        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
                        initialize_app(cred)
                        logger.info("✅ Firebase initialized with environment variables")
                    else:
                        # Fallback to test mode
                        logger.warning("⚠️ No Firebase credentials found, using test mode")
                        cls._test_mode = True
                        cls._initialized = True
                        return
                
                cls._initialized = True
                cls._test_mode = False
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Firebase: {str(e)}")
                logger.warning("⚠️ Falling back to test mode")
                cls._test_mode = True
                cls._initialized = True
    
    @classmethod
    def send_to_all_users(cls, title: str, body: str, data: Dict = None) -> Dict:
        """Send notification to all active users"""
        cls._initialize_firebase()
        
        try:
            # Get all active FCM tokens
            active_tokens = list(FcmToken.objects.filter(
                is_active=True,
                notifications_enabled=True
            ).values_list('fcm_token', flat=True))
            
            if not active_tokens:
                logger.warning("No active FCM tokens found")
                return {'success_count': 0, 'failure_count': 0, 'message': 'No active tokens'}
            
            # Test mode (when Firebase is not available)
            if cls._test_mode:
                logger.info(f"TEST MODE - Would send notification:")
                logger.info(f"Title: {title}")
                logger.info(f"Body: {body}")
                logger.info(f"To {len(active_tokens)} devices")
                
                # Update last_used for test
                FcmToken.objects.filter(
                    is_active=True,
                    notifications_enabled=True
                ).update(last_used=timezone.now())
                
                return {
                    'success_count': len(active_tokens),
                    'failure_count': 0,
                    'message': f'TEST: Would send to {len(active_tokens)} devices'
                }
            
            # Real Firebase sending
            total_success = 0
            total_failure = 0
            
            # Send in batches of 500 (FCM limit)
            for i in range(0, len(active_tokens), 500):
                batch_tokens = active_tokens[i:i + 500]
                success, failure = cls._send_multicast(batch_tokens, title, body, data)
                total_success += success
                total_failure += failure
            
            logger.info(f"📱 Real notification sent: {total_success} success, {total_failure} failed")
            
            return {
                'success_count': total_success,
                'failure_count': total_failure,
                'message': f'Sent to {total_success}/{len(active_tokens)} devices'
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to send notifications: {str(e)}")
            return {'success_count': 0, 'failure_count': 0, 'message': f'Error: {str(e)}'}
    
    @classmethod
    def _send_multicast(cls, tokens: List[str], title: str, body: str, data: Dict = None) -> tuple:
        """Send notification to multiple tokens using real Firebase"""
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in (data or {}).items()},
                tokens=tokens,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        channel_id='default_channel',
                        sound='default',
                        icon='ic_notification',
                        color='#FF6B6B',
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(title=title, body=body),
                            sound='default',
                            badge=1,
                        ),
                    ),
                ),
            )
            
            response = messaging.send_multicast(message)
            
            # Handle failed tokens
            if response.failure_count > 0:
                failed_tokens = []
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        failed_token = tokens[idx]
                        error = resp.exception
                        
                        # Deactivate invalid tokens
                        if isinstance(error, (messaging.UnregisteredError, messaging.SenderIdMismatchError)):
                            FcmToken.objects.filter(fcm_token=failed_token).update(is_active=False)
                            logger.info(f"Deactivated invalid token: {failed_token[:20]}...")
                        
                        failed_tokens.append(failed_token)
            
            # Update last_used for successful tokens
            successful_tokens = [tokens[idx] for idx, resp in enumerate(response.responses) if resp.success]
            if successful_tokens:
                FcmToken.objects.filter(fcm_token__in=successful_tokens).update(last_used=timezone.now())
            
            return response.success_count, response.failure_count
            
        except Exception as e:
            logger.error(f"❌ Multicast send failed: {str(e)}")
            return 0, len(tokens)
    
    @classmethod
    def send_new_result_notification(cls, lottery_name: str) -> Dict:
        """Send notification when new result is added"""
        title = "🎯 New Kerala Lottery Results!"
        body = f"Fresh {lottery_name} results are being added. Check them out now!"
        
        data = {
            'type': 'new_result',
            'lottery_name': lottery_name,
            'click_action': 'OPEN_RESULTS'
        }
        
        return cls.send_to_all_users(title, body, data)
    
    @classmethod
    def send_result_ready_notification(cls, lottery_name: str, draw_number: str) -> Dict:
        """Send notification when result is ready (checkbox ticked)"""
        title = "🎉 Lottery Results Ready!"
        body = f"{lottery_name} Draw {draw_number} results are now available. Check if you won!"
        
        data = {
            'type': 'result_ready',
            'lottery_name': lottery_name,
            'draw_number': draw_number,
            'click_action': 'OPEN_RESULTS'
        }
        
        return cls.send_to_all_users(title, body, data)