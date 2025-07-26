# Replace your results/services/fcm_service.py with this updated version:

import logging
from typing import List, Dict
from django.conf import settings
from django.utils import timezone
from firebase_admin import credentials, messaging, initialize_app
import firebase_admin
from results.models import FcmToken

logger = logging.getLogger('lottery_app')

class FCMService:
    """Production-ready Firebase FCM service with image support"""
    
    _initialized = False
    _test_mode = False
    
    # 🖼️ LOTTERY IMAGE MAPPING
    LOTTERY_IMAGES = {
        'KARUNYA': 'https://res.cloudinary.com/drzk2a53l/image/upload/v1753541778/karunya_n2vmqa.jpg',
        'SAMRUDHI': 'https://res.cloudinary.com/drzk2a53l/image/upload/v1753541778/samrudhi_is5z5p.jpg',
        'VISHU BUMPER': 'https://res.cloudinary.com/drzk2a53l/image/upload/v1753541778/vishu-bumper_rr41x3.jpg',
        'SUMMER BUMPER': 'https://res.cloudinary.com/drzk2a53l/image/upload/v1753541778/summer-bumper_peqaaf.jpg',
        'MANSOON BUMPER': 'https://res.cloudinary.com/drzk2a53l/image/upload/v1753541778/manusoonbumper_dlgubn.jpg',
        'BHAGYATHARA': 'https://res.cloudinary.com/drzk2a53l/image/upload/v1753541790/bhagyadhara_qhxlez.jpg',
        'KARUNYA PLUS': 'https://res.cloudinary.com/drzk2a53l/image/upload/v1753541791/karunya-plus_baoqxn.jpg',
        'STHREE SAKTHI': 'https://res.cloudinary.com/drzk2a53l/image/upload/v1753541791/sthreesakthi_pyyej4.jpg',
        'DHANALEKSHMI': 'https://res.cloudinary.com/drzk2a53l/image/upload/v1753541791/dhanalakshmi_fs8f9o.jpg',
        'SUVARNA KERALAM': 'https://res.cloudinary.com/drzk2a53l/image/upload/v1753541791/suvarnna-keralam_tnqdre.jpg'
    }
    
    # 🎯 DEFAULT IMAGES
    FALLBACK_IMAGE = 'https://res.cloudinary.com/drzk2a53l/image/upload/v1753542621/logo_foreground_512_ssofyu.png'
    NOTIFICATION_ICON = 'https://res.cloudinary.com/drzk2a53l/image/upload/v1753542621/logo_foreground_512_ssofyu.png'
    
    @classmethod
    def _get_lottery_image(cls, lottery_name: str) -> str:
        """Get the appropriate image URL for a lottery"""
        # Convert to uppercase and try exact match first
        lottery_upper = lottery_name.upper().strip()
        
        # Direct match
        if lottery_upper in cls.LOTTERY_IMAGES:
            return cls.LOTTERY_IMAGES[lottery_upper]
        
        # Fuzzy matching for common variations
        for key in cls.LOTTERY_IMAGES:
            if key in lottery_upper or lottery_upper in key:
                return cls.LOTTERY_IMAGES[key]
        
        # Return fallback image
        logger.warning(f"No image found for lottery: {lottery_name}, using fallback")
        return cls.FALLBACK_IMAGE
    
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
    def send_to_all_users(cls, title: str, body: str, data: Dict = None, image_url: str = None) -> Dict:
        """Send notification to all active users with image support"""
        try:
            from firebase_admin import messaging
            from results.models import FcmToken
            from django.utils import timezone
            import logging
            
            logger = logging.getLogger('lottery_app')
            
            # Initialize Firebase if needed
            cls._initialize_firebase()
            
            # Get all active FCM tokens
            active_tokens = list(FcmToken.objects.filter(
                is_active=True,
                notifications_enabled=True
            ).values_list('fcm_token', flat=True))
            
            if not active_tokens:
                logger.warning("No active FCM tokens found")
                return {'success_count': 0, 'failure_count': 0, 'message': 'No active tokens'}
            
            # Use fallback image if no image provided
            if not image_url:
                image_url = cls.FALLBACK_IMAGE
            
            # Send using proven working direct method with images
            success_count = 0
            failure_count = 0
            
            for token in active_tokens:
                try:
                    # Create notification with image support
                    notification = messaging.Notification(
                        title=title,
                        body=body,
                        image=image_url  # Big picture when expanded
                    )
                    
                    # Android-specific configuration
                    android_config = messaging.AndroidConfig(
                        priority='high',
                        notification=messaging.AndroidNotification(
                            channel_id='default_channel',
                            sound='default',
                            icon='ic_notification',  # App icon (small)
                            color='#FF6B6B',
                            image=image_url,  # Big picture style
                            click_action='OPEN_RESULTS'
                        ),
                    )
                    
                    # iOS-specific configuration
                    apns_config = messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                alert=messaging.ApsAlert(title=title, body=body),
                                sound='default',
                                badge=1,
                                thread_id='lottery_results'
                            ),
                            # iOS doesn't support images in basic notifications
                            # but we can add custom data for rich notifications
                        ),
                        headers={
                            'apns-push-type': 'alert',
                            'apns-priority': '10'
                        }
                    )
                    
                    message = messaging.Message(
                        notification=notification,
                        data={k: str(v) for k, v in (data or {}).items()},
                        token=token,
                        android=android_config,
                        apns=apns_config
                    )
                    
                    response = messaging.send(message)
                    success_count += 1
                    logger.info(f"✅ Notification sent with image: {response}")
                    
                except Exception as e:
                    failure_count += 1
                    logger.error(f"❌ Notification failed: {e}")
                    
                    # Deactivate invalid tokens
                    if "not a valid FCM registration token" in str(e) or "Requested entity was not found" in str(e):
                        FcmToken.objects.filter(fcm_token=token).update(is_active=False)
                        logger.info(f"🗑️ Deactivated invalid token")
            
            # Update last_used for successful tokens
            if success_count > 0:
                FcmToken.objects.filter(
                    fcm_token__in=active_tokens,
                    is_active=True
                ).update(last_used=timezone.now())
            
            logger.info(f"📱 Notification summary: {success_count} success, {failure_count} failed")
            
            return {
                'success_count': success_count,
                'failure_count': failure_count,
                'message': f'Sent to {success_count}/{len(active_tokens)} devices',
                'image_url': image_url
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to send notifications: {str(e)}")
            return {'success_count': 0, 'failure_count': 0, 'message': f'Error: {str(e)}'}
    
    @classmethod
    def _send_multicast(cls, tokens: List[str], title: str, body: str, data: Dict = None, image_url: str = None) -> tuple:
        """Send notification to multiple tokens using real Firebase with image support"""
        try:
            # Use fallback image if no image provided
            if not image_url:
                image_url = cls.FALLBACK_IMAGE
            
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title, 
                    body=body,
                    image=image_url
                ),
                data={k: str(v) for k, v in (data or {}).items()},
                tokens=tokens,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        channel_id='default_channel',
                        sound='default',
                        icon='ic_notification',
                        color='#FF6B6B',
                        image=image_url,
                        click_action='OPEN_RESULTS'
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(title=title, body=body),
                            sound='default',
                            badge=1,
                            thread_id='lottery_results'
                        ),
                    ),
                    headers={
                        'apns-push-type': 'alert',
                        'apns-priority': '10'
                    }
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
        """Send notification when new result is added with lottery-specific image"""
        title = f"🎯 {lottery_name} Results Live!"
        body = f"Fresh {lottery_name} results are being added. Check them out now!"
        
        # Get the appropriate image for this lottery
        image_url = cls._get_lottery_image(lottery_name)
        
        data = {
            'type': 'new_result',
            'lottery_name': lottery_name,
            'click_action': 'OPEN_RESULTS',
            'image_url': image_url
        }
        
        logger.info(f"📸 Sending notification for {lottery_name} with image: {image_url}")
        
        return cls.send_to_all_users(title, body, data, image_url)
    
    @classmethod
    def send_result_ready_notification(cls, lottery_name: str, draw_number: str) -> Dict:
        """Send notification when result is ready with lottery-specific image"""
        title = f"🎉 {lottery_name} Results Ready!"
        body = f"{lottery_name} Draw {draw_number} results are now available. Check if you won!"
        
        # Get the appropriate image for this lottery
        image_url = cls._get_lottery_image(lottery_name)
        
        data = {
            'type': 'result_ready',
            'lottery_name': lottery_name,
            'draw_number': draw_number,
            'click_action': 'OPEN_RESULTS',
            'image_url': image_url
        }
        
        logger.info(f"📸 Sending ready notification for {lottery_name} with image: {image_url}")
        
        return cls.send_to_all_users(title, body, data, image_url)

    @classmethod
    def test_notification_with_image(cls, lottery_name: str = "KARUNYA") -> Dict:
        """Test method to send a sample notification with image"""
        title = "🧪 Test Notification"
        body = f"Testing {lottery_name} notification with image support"
        
        image_url = cls._get_lottery_image(lottery_name)
        
        data = {
            'type': 'test',
            'lottery_name': lottery_name,
            'click_action': 'OPEN_RESULTS'
        }
        
        logger.info(f"🧪 Testing notification with image: {image_url}")
        
        return cls.send_to_all_users(title, body, data, image_url)