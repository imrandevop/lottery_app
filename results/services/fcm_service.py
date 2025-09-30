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
    def send_to_all_users_batched(cls, title: str, body: str, data: Dict = None, image_url: str = None) -> Dict:
        """
        SCALABLE: Send notifications using Firebase batch messaging
        Handles 10,000+ users efficiently using multicast messages
        """
        try:
            from firebase_admin import messaging
            from results.models import FcmToken
            import logging
            import threading
            from concurrent.futures import ThreadPoolExecutor, as_completed

            logger = logging.getLogger('lottery_app')

            # Initialize Firebase if needed
            cls._initialize_firebase()

            # Get all active FCM tokens in batches
            batch_size = 500  # Firebase multicast limit
            active_tokens = FcmToken.objects.filter(
                is_active=True,
                notifications_enabled=True
            ).values_list('fcm_token', flat=True)

            total_tokens = active_tokens.count()

            if total_tokens == 0:
                logger.warning("No active FCM tokens found")
                return {'success_count': 0, 'failure_count': 0, 'message': 'No active tokens'}

            logger.info(f"Sending notifications to {total_tokens} users using batch processing")

            # Use fallback image if no image provided
            if not image_url:
                image_url = cls.FALLBACK_IMAGE

            # Build the message template
            message_template = cls._build_multicast_message(title, body, data, image_url)

            # Process in batches using thread pool for parallel processing
            total_success = 0
            total_failure = 0

            # Create batches of tokens
            token_batches = []
            for i in range(0, total_tokens, batch_size):
                batch_tokens = list(active_tokens[i:i + batch_size])
                token_batches.append(batch_tokens)

            logger.info(f"📦 Created {len(token_batches)} batches of max {batch_size} tokens each")

            # Use ThreadPoolExecutor for parallel batch processing
            max_workers = min(10, len(token_batches))  # Max 10 concurrent batches

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all batch jobs
                future_to_batch = {
                    executor.submit(cls._send_batch_multicast, message_template, batch_tokens, batch_idx): batch_idx
                    for batch_idx, batch_tokens in enumerate(token_batches)
                }

                # Collect results as they complete
                for future in as_completed(future_to_batch):
                    batch_idx = future_to_batch[future]
                    try:
                        batch_result = future.result()
                        total_success += batch_result['success_count']
                        total_failure += batch_result['failure_count']

                        logger.info(f"✅ Batch {batch_idx + 1} completed: "
                                  f"{batch_result['success_count']} success, "
                                  f"{batch_result['failure_count']} failed")

                    except Exception as e:
                        logger.error(f"❌ Batch {batch_idx + 1} failed: {e}")
                        total_failure += len(token_batches[batch_idx])

            success_rate = (total_success / total_tokens * 100) if total_tokens > 0 else 0

            logger.info(f"🎯 Batch notification completed: {total_success}/{total_tokens} "
                       f"({success_rate:.1f}% success rate)")

            return {
                'success_count': total_success,
                'failure_count': total_failure,
                'total_tokens': total_tokens,
                'success_rate': success_rate,
                'message': f'Sent to {total_success}/{total_tokens} devices ({success_rate:.1f}% success)'
            }

        except Exception as e:
            logger.error(f"❌ Batch notification system failed: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")

            # Fallback to old method for small user bases
            if total_tokens < 100:
                logger.info("🔄 Falling back to sequential method for small user base")
                return cls.send_to_all_users_sequential(title, body, data, image_url)

            return {
                'success_count': 0,
                'failure_count': total_tokens,
                'message': f'Batch system failed: {str(e)}'
            }

    @classmethod
    def _build_multicast_message(cls, title: str, body: str, data: Dict = None, image_url: str = None):
        """Build Firebase multicast message template"""
        from firebase_admin import messaging

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
                )
            ),
            headers={
                'apns-push-type': 'alert',
                'apns-priority': '10'
            }
        )

        return {
            'notification': messaging.Notification(title=title, body=body),
            'data': {**{k: str(v) for k, v in (data or {}).items()}},
            'android': android_config,
            'apns': apns_config
        }

    @classmethod
    def _send_batch_multicast(cls, message_template: Dict, tokens: List[str], batch_idx: int) -> Dict:
        """Send multicast message to a batch of tokens"""
        try:
            from firebase_admin import messaging
            import logging

            logger = logging.getLogger('lottery_app')

            # Create multicast message
            multicast_message = messaging.MulticastMessage(
                tokens=tokens,
                **message_template
            )

            # Send multicast (up to 500 tokens at once)
            response = messaging.send_multicast(multicast_message)

            # Process response
            success_count = response.success_count
            failure_count = response.failure_count

            # Log failed tokens for debugging (optional)
            if response.responses:
                failed_tokens = []
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        failed_tokens.append({
                            'token_preview': tokens[idx][:20] + '...',
                            'error': str(resp.exception) if resp.exception else 'Unknown'
                        })

                if failed_tokens:
                    logger.warning(f"⚠️ Batch {batch_idx + 1} had {len(failed_tokens)} failed tokens")

            return {
                'success_count': success_count,
                'failure_count': failure_count,
                'batch_size': len(tokens)
            }

        except Exception as e:
            logger.error(f"❌ Multicast batch {batch_idx + 1} failed: {e}")
            return {
                'success_count': 0,
                'failure_count': len(tokens),
                'batch_size': len(tokens)
            }

    @classmethod
    def send_to_all_users(cls, title: str, body: str, data: Dict = None, image_url: str = None) -> Dict:
        """
        Smart notification dispatcher:
        - Uses batched multicast for 100+ users (scalable)
        - Uses sequential for <100 users (simple)
        """
        from results.models import FcmToken

        # Check user count to decide method
        user_count = FcmToken.objects.filter(is_active=True, notifications_enabled=True).count()

        if user_count >= 100:  # Use batched for 100+ users
            # Use scalable batch system for larger user bases
            return cls.send_to_all_users_batched(title, body, data, image_url)
        else:
            # Use simple sequential for smaller user bases (works reliably)
            return cls.send_to_all_users_sequential(title, body, data, image_url)

    @classmethod
    def send_to_all_users_sequential(cls, title: str, body: str, data: Dict = None, image_url: str = None) -> Dict:
        """LEGACY: Send notification to all active users sequentially (for small user bases)"""
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
                    # Create base notification without image (to ensure proper icon display)
                    notification = messaging.Notification(
                        title=title,
                        body=body
                        # Don't set image here - it affects the small icon
                    )
                    
                    # Android-specific configuration with proper icon/image separation
                    android_config = messaging.AndroidConfig(
                        priority='high',
                        notification=messaging.AndroidNotification(
                            channel_id='default_channel',
                            sound='default',
                            icon='ic_notification',  # Your app's small icon on left
                            color='#FF6B6B',
                            image=image_url,  # Big picture ONLY when expanded
                            click_action='FLUTTER_NOTIFICATION_CLICK',
                            tag='lottery_notification'
                        ),
                        # Add image as data for better control
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
                        data={
                            **{k: str(v) for k, v in (data or {}).items()},
                            'image_url': image_url,  # Pass image as data
                            'notification_icon': cls.NOTIFICATION_ICON
                        },
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
                    body=body
                    # No image here to avoid affecting small icon
                ),
                data={
                    **{k: str(v) for k, v in (data or {}).items()},
                    'image_url': image_url,
                    'notification_icon': cls.NOTIFICATION_ICON
                },
                tokens=tokens,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        channel_id='default_channel',
                        sound='default',
                        icon='ic_notification',  # App icon on left
                        color='#FF6B6B',
                        image=image_url,  # Big picture when expanded
                        click_action='OPEN_RESULTS',
                        tag='lottery_notification'
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
        
        logger.info(f"Sending notification for {lottery_name} with image: {image_url}")
        
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
        
        logger.info(f"Sending ready notification for {lottery_name} with image: {image_url}")
        
        return cls.send_to_all_users(title, body, data, image_url)

