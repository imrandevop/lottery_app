# FCM Service for Lottery Lite Version
# Copy this file to your lite version Django app

import logging
from typing import List, Dict
from django.conf import settings
from django.utils import timezone
from firebase_admin import credentials, messaging, initialize_app
import firebase_admin

logger = logging.getLogger('lottery_lite_app')

class FCMLiteService:
    """Firebase FCM service for Lottery Lite Version"""
    
    _initialized = False
    _test_mode = False
    
    # 🖼️ LOTTERY IMAGE MAPPING (Customize for Lite version)
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
    
    # 🎯 DEFAULT IMAGES (Update with your lite app's logo)
    FALLBACK_IMAGE = 'https://res.cloudinary.com/drzk2a53l/image/upload/v1753542621/logo_foreground_512_ssofyu.png'
    NOTIFICATION_ICON = 'https://res.cloudinary.com/drzk2a53l/image/upload/v1753542621/logo_foreground_512_ssofyu.png'
    
    @classmethod
    def _get_lottery_image(cls, lottery_name: str) -> str:
        """Get the appropriate image URL for a lottery"""
        lottery_upper = lottery_name.upper().strip()
        
        # Direct match
        if lottery_upper in cls.LOTTERY_IMAGES:
            return cls.LOTTERY_IMAGES[lottery_upper]
        
        # Fuzzy matching
        for key in cls.LOTTERY_IMAGES:
            if key in lottery_upper or lottery_upper in key:
                return cls.LOTTERY_IMAGES[key]
        
        logger.warning(f"No image found for lottery: {lottery_name}, using fallback")
        return cls.FALLBACK_IMAGE
    
    @classmethod
    def _initialize_firebase(cls):
        """Initialize Firebase Admin SDK for Lite Version"""
        if not cls._initialized:
            try:
                if not firebase_admin._apps:
                    # Try to get credentials
                    if hasattr(settings, 'FIREBASE_CREDENTIALS_FILE'):
                        # Development: Use service account file
                        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_FILE)
                        initialize_app(cred)
                        logger.info("✅ Firebase Lite initialized with service account file")
                    elif hasattr(settings, 'FIREBASE_CREDENTIALS') and settings.FIREBASE_CREDENTIALS:
                        # Production: Use environment variables
                        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
                        initialize_app(cred)
                        logger.info("✅ Firebase Lite initialized with environment variables")
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
        """
        Send notifications to all active users
        Uses sequential method to avoid HTTP/2 protocol issues
        """
        try:
            from firebase_admin import messaging
            # Import FcmToken from your models
            from .models import FcmToken  # Update import path as needed
            from django.utils import timezone
            import logging
            import threading
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import time

            logger = logging.getLogger('lottery_lite_app')

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

            logger.info(f"🚀 Sending to {len(active_tokens)} users using parallel threads")

            # Thread-safe counters
            success_count = 0
            failure_count = 0
            success_lock = threading.Lock()
            failure_lock = threading.Lock()

            def send_single_notification(token):
                """Send notification to a single token (thread-safe)"""
                nonlocal success_count, failure_count
                try:
                    # Create notification
                    notification = messaging.Notification(
                        title=title,
                        body=body
                    )
                    
                    # Android-specific configuration
                    android_config = messaging.AndroidConfig(
                        priority='high',
                        notification=messaging.AndroidNotification(
                            channel_id='default_channel',
                            sound='default',
                            icon='ic_notification',
                            color='#FF6B6B',
                            image=image_url,
                            click_action='FLUTTER_NOTIFICATION_CLICK',
                            tag='lottery_notification'
                        ),
                        data={
                            'image_url': image_url,
                            'big_picture': 'true'
                        }
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
                        ),
                        headers={
                            'apns-push-type': 'alert',
                            'apns-priority': '10'
                        }
                    )
                    
                    message = messaging.Message(
                        notification=notification,
                        data={
                            **{k: str(v) for k, v in (data or {}).items()},
                            'image_url': image_url,
                            'notification_icon': cls.NOTIFICATION_ICON
                        },
                        token=token,
                        android=android_config,
                        apns=apns_config
                    )
                    
                    response = messaging.send(message)
                    with success_lock:
                        success_count += 1
                    return True

                except Exception as e:
                    with failure_lock:
                        failure_count += 1
                    error_str = str(e)

                    # Deactivate invalid tokens
                    if ("not a valid FCM registration token" in error_str or
                        "Requested entity was not found" in error_str or
                        "registration-token-not-registered" in error_str):
                        FcmToken.objects.filter(fcm_token=token).update(is_active=False)

                    time.sleep(0.05)
                    return False

            # 🚀 PARALLEL EXECUTION
            start_time = time.time()
            max_workers = min(20, len(active_tokens))

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_token = {
                    executor.submit(send_single_notification, token): token
                    for token in active_tokens
                }

                completed = 0
                for future in as_completed(future_to_token):
                    completed += 1
                    if completed % 100 == 0:
                        logger.info(f"📊 Progress: {completed}/{len(active_tokens)} notifications processed")

            elapsed_time = time.time() - start_time
            rate = len(active_tokens) / elapsed_time if elapsed_time > 0 else 0

            # Update last_used for successful tokens
            if success_count > 0:
                FcmToken.objects.filter(
                    fcm_token__in=active_tokens,
                    is_active=True
                ).update(last_used=timezone.now())

            logger.info(f"🚀 NOTIFICATION COMPLETE: {success_count} success, {failure_count} failed")
            logger.info(f"⚡ Performance: {len(active_tokens)} notifications in {elapsed_time:.2f}s ({rate:.1f}/sec)")

            return {
                'success_count': success_count,
                'failure_count': failure_count,
                'message': f'Sent to {success_count}/{len(active_tokens)} devices in {elapsed_time:.2f}s',
                'image_url': image_url,
                'elapsed_time': elapsed_time,
                'notifications_per_second': rate
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to send notifications: {str(e)}")
            return {'success_count': 0, 'failure_count': 0, 'message': f'Error: {str(e)}'}
    
    @classmethod
    def send_new_result_notification(cls, lottery_name: str) -> Dict:
        """Send notification when new result is added"""
        title = f"🎯 {lottery_name} Results Live! [Lite]"
        body = f"Fresh {lottery_name} results are being added. Check them out now!"
        
        image_url = cls._get_lottery_image(lottery_name)
        
        data = {
            'type': 'new_result',
            'lottery_name': lottery_name,
            'click_action': 'OPEN_RESULTS',
            'image_url': image_url
        }
        
        logger.info(f"Sending notification for {lottery_name} with image: {image_url}")
        
        return cls.send_to_all_users(title, body, data, image_url)
    
    @classmethod
    def send_result_ready_notification(cls, lottery_name: str, draw_number: str) -> Dict:
        """Send notification when result is ready"""
        title = f"🎉 {lottery_name} Results Ready!"
        body = f"{lottery_name} Draw {draw_number} results are now available. Check if you won!"
        
        image_url = cls._get_lottery_image(lottery_name)
        
        data = {
            'type': 'result_ready',
            'lottery_name': lottery_name,
            'draw_number': draw_number,
            'click_action': 'OPEN_RESULTS',
            'image_url': image_url
        }
        
        logger.info(f"Sending ready notification for {lottery_name} with image: {image_url}")
        
        return cls.send_to_all_users(title, body, data, image_url)
    
    @classmethod
    def send_custom_notification(cls, title: str, body: str, image_url: str = None, data: Dict = None) -> Dict:
        """
        Send custom notification to all users
        Useful for announcements, updates, etc.
        """
        if not image_url:
            image_url = cls.FALLBACK_IMAGE
        
        return cls.send_to_all_users(title, body, data or {}, image_url)
    
    @classmethod
    def send_to_specific_user(cls, fcm_token: str, title: str, body: str, data: Dict = None, image_url: str = None) -> Dict:
        """Send notification to a specific user by FCM token"""
        try:
            from firebase_admin import messaging
            
            cls._initialize_firebase()
            
            if not image_url:
                image_url = cls.FALLBACK_IMAGE
            
            notification = messaging.Notification(title=title, body=body)
            
            android_config = messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    channel_id='default_channel',
                    sound='default',
                    icon='ic_notification',
                    color='#FF6B6B',
                    image=image_url,
                    click_action='FLUTTER_NOTIFICATION_CLICK',
                ),
            )
            
            message = messaging.Message(
                notification=notification,
                data={**{k: str(v) for k, v in (data or {}).items()}, 'image_url': image_url},
                token=fcm_token,
                android=android_config,
            )
            
            response = messaging.send(message)
            logger.info(f"✅ Notification sent to user: {response}")
            
            return {'success': True, 'message': 'Notification sent successfully'}
            
        except Exception as e:
            logger.error(f"❌ Failed to send notification to user: {str(e)}")
            return {'success': False, 'message': f'Error: {str(e)}'}


# Example Usage:
"""
# Send notification when new result is published
from fcm_service_lite import FCMLiteService

result = FCMLiteService.send_new_result_notification(
    lottery_name="KARUNYA"
)
print(result)

# Send custom notification
result = FCMLiteService.send_custom_notification(
    title="🎊 Special Offer!",
    body="Get 50% off on all lottery predictions today!",
    image_url="https://example.com/offer-image.jpg"
)
print(result)

# Send to specific user
result = FCMLiteService.send_to_specific_user(
    fcm_token="user_fcm_token_here",
    title="Personal Message",
    body="Hello, your result is ready!"
)
print(result)
"""
