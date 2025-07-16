# results/management/commands/test_notifications.py

from django.core.management.base import BaseCommand
from results.services.fcm_service import FCMService
from results.models import NotificationLog
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Test Firebase push notifications'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            default='test',
            choices=['test', 'started', 'completed'],
            help='Type of notification to send'
        )
        parser.add_argument(
            '--lottery',
            type=str,
            default='Karunya',
            help='Lottery name for started/completed notifications'
        )
        parser.add_argument(
            '--draw',
            type=str,
            default='KR-123',
            help='Draw number for completed notifications'
        )
    
    def handle(self, *args, **options):
        notification_type = options['type']
        lottery_name = options['lottery']
        draw_number = options['draw']
        
        self.stdout.write(f"🧪 Testing {notification_type} notification...")
        
        # Check if we have any FCM tokens
        token_count = User.objects.filter(
            fcm_token__isnull=False,
            notifications_enabled=True
        ).exclude(fcm_token='').count()
        
        if token_count == 0:
            self.stdout.write(
                self.style.WARNING('⚠️  No FCM tokens found. Please register some tokens first.')
            )
            return
        
        self.stdout.write(f"📱 Found {token_count} registered devices")
        
        try:
            if notification_type == 'test':
                result = FCMService.test_notification()
            elif notification_type == 'started':
                result = FCMService.send_lottery_result_started(lottery_name)
            elif notification_type == 'completed':
                result = FCMService.send_lottery_result_completed(lottery_name, draw_number)
            
            # Display results
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Notification sent successfully!\n"
                    f"   Success: {result['success_count']}\n"
                    f"   Failed: {result['failure_count']}\n"
                    f"   Invalid tokens cleaned: {len(result.get('invalid_tokens', []))}"
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Failed to send notification: {e}")
            )