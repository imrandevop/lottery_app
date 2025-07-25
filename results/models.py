from django.db import models
import uuid
from django.utils import timezone
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)
import re
import pytz
from datetime import date, timedelta
import random
from django.db import transaction


class Lottery(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    first_price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Lottery"
        verbose_name_plural = "Lotteries"


class LotteryResult(models.Model):
    # ... your existing fields ...
    unique_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    lottery = models.ForeignKey(Lottery, on_delete=models.CASCADE)
    date = models.DateField()
    draw_number = models.CharField(max_length=50)
    is_published = models.BooleanField(default=False, verbose_name="Published")
    is_bumper = models.BooleanField(default=False, verbose_name="Bumper")
    results_ready_notification = models.BooleanField(
        default=False, 
        verbose_name="Notify",
        help_text="Send 'Results Ready' notification to users"
    )
    
    # 🔥 ADD THIS NEW FIELD:
    notification_sent = models.BooleanField(
        default=False,
        verbose_name="Notification Sent",
        help_text="Whether notification has been sent to users"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PrizeEntry(models.Model):
    PRIZE_CHOICES = [
        ('1st', '1st Prize'),
        ('2nd', '2nd Prize'),
        ('3rd', '3rd Prize'),
        ('4th', '4th Prize'),
        ('5th', '5th Prize'),
        ('6th', '6th Prize'),
        ('7th', '7th Prize'),
        ('8th', '8th Prize'),
        ('9th', '9th Prize'),
        ('10th', '10th Prize'),
        ('consolation', 'Consolation Prize'),
    ]
    
    lottery_result = models.ForeignKey(LotteryResult, on_delete=models.CASCADE, related_name='prizes')
    prize_type = models.CharField(max_length=20, choices=PRIZE_CHOICES)
    prize_amount = models.DecimalField(max_digits=12, decimal_places=2)
    ticket_number = models.CharField(max_length=50)
    place = models.CharField(max_length=100, blank=True, null=True)  # Only for 1st, 2nd, 3rd prizes
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.lottery_result} - {self.get_prize_type_display()} - {self.ticket_number}"
    
    class Meta:
        verbose_name = "Prize Entry"
        verbose_name_plural = "Prize Entries"


class ImageUpdate(models.Model):
    """
    Model to manage update images for home screen
    """
    # Update Images
    update_image1 = models.URLField(
        max_length=1000, 
        verbose_name="Update Image 1 URL",
        help_text="URL for the first update image"
    )
    update_image2 = models.URLField(
        max_length=1000, 
        verbose_name="Update Image 2 URL",
        help_text="URL for the second update image"
    )
    update_image3 = models.URLField(
        max_length=1000, 
        verbose_name="Update Image 3 URL",
        help_text="URL for the third update image"
    )
    
    # Redirect Links for each image
    redirect_link1 = models.URLField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name="Redirect Link 1",
        help_text="URL to redirect when user taps on image 1"
    )
    redirect_link2 = models.URLField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name="Redirect Link 2",
        help_text="URL to redirect when user taps on image 2"
    )
    redirect_link3 = models.URLField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name="Redirect Link 3",
        help_text="URL to redirect when user taps on image 3"
    )
    
    # Meta fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Image Updates (Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"
    
    class Meta:
        verbose_name = "Image Update"
        verbose_name_plural = "Image Updates"
        ordering = ['-updated_at']  # Show newest first
    
    
    @classmethod
    def get_images(cls):
        """Get the latest image settings instance, create default if none exists"""
        # Get the most recent instance (ordering = ['-updated_at'] makes first() return the newest)
        latest_instance = cls.objects.first()
        
        if not latest_instance:
            # Create a new default instance (let Django auto-assign the ID)
            latest_instance = cls.objects.create(
                update_image1='https://example.com/default-image1.jpg',
                update_image2='https://example.com/default-image2.jpg',
                update_image3='https://example.com/default-image3.jpg',
                redirect_link1='https://example.com/redirect1',
                redirect_link2='https://example.com/redirect2',
                redirect_link3='https://example.com/redirect3',
            )
        
        return latest_instance
    

# <---------------NEWS SECTION---------------->
class News(models.Model):
    headline = models.CharField(max_length=255, help_text="News headline")
    content = models.TextField(help_text="News content/description")
    image_url = models.URLField(max_length=500, help_text="Image URL for the news")
    news_url = models.URLField(max_length=500, help_text="Original news URL")
    source = models.CharField(max_length=100, default="News Source", help_text="News source name")
    published_at = models.DateTimeField(default=timezone.now, help_text="Publication date and time")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text="Is this news active?")

    class Meta:
        verbose_name = "News Article"
        verbose_name_plural = "News Articles"
        ordering = ['-published_at']

    def __str__(self):
        return self.headline

#<---------------PREDICTION SECTION ---------------->

# lottery_prediction/models.py

class PredictionModel(models.Model):
    """Store different prediction models and their configurations"""
    ALGORITHM_CHOICES = [
        ('frequency', 'Frequency Analysis'),
        ('lstm', 'LSTM Neural Network'),
        ('pattern', 'Pattern Recognition'),
        ('ensemble', 'Ensemble Method'),
    ]
    
    name = models.CharField(max_length=100)
    algorithm = models.CharField(max_length=20, choices=ALGORITHM_CHOICES)
    lottery_type = models.CharField(max_length=100, blank=True)  # Empty for all lotteries
    prize_type = models.CharField(max_length=20, blank=True)  # Empty for all prize types
    accuracy_score = models.FloatField(default=0.0)
    parameters = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.get_algorithm_display()}"

class PredictionHistory(models.Model):
    """Store prediction history for performance tracking with enhanced stability"""
    lottery_name = models.CharField(max_length=200)
    prize_type = models.CharField(max_length=20)
    predicted_numbers = models.JSONField()
    actual_numbers = models.JSONField(null=True, blank=True)
    prediction_date = models.DateTimeField(auto_now_add=True)
    draw_date = models.DateField(null=True, blank=True)
    accuracy_score = models.FloatField(null=True, blank=True)
    model_used = models.ForeignKey(PredictionModel, on_delete=models.SET_NULL, null=True)
    
    # New fields for stability tracking
    is_stable = models.BooleanField(default=True, help_text="Whether this prediction should remain stable")
    cycle_identifier = models.CharField(max_length=100, blank=True, help_text="Identifies the prediction cycle")
    
    class Meta:
        ordering = ['-prediction_date']
        indexes = [
            models.Index(fields=['lottery_name', 'prize_type', '-prediction_date']),
            models.Index(fields=['lottery_name', 'prize_type', 'is_stable']),
        ]
    
    def __str__(self):
        return f"{self.lottery_name} - {self.prize_type} - {self.prediction_date.date()}"
    
    def save(self, *args, **kwargs):
        # Auto-generate cycle identifier if not provided
        if not self.cycle_identifier:
            india_tz = pytz.timezone('Asia/Kolkata')
            pred_date = self.prediction_date.astimezone(india_tz) if self.prediction_date else timezone.now().astimezone(india_tz)
            # Format: LOTTERY_PRIZETYPE_YYYY_WW (year and week number)
            week_num = pred_date.isocalendar()[1]
            self.cycle_identifier = f"{self.lottery_name.upper()}_{self.prize_type}_{pred_date.year}_{week_num:02d}"
        
        super().save(*args, **kwargs)


#<---------------LIVE SECTION---------------->
class LiveVideo(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('ended', 'Ended'),
        ('cancelled', 'Cancelled'),
    ]
    
    lottery_name = models.CharField(max_length=200, help_text="Name of the lottery/event")
    youtube_url = models.URLField(
        max_length=500,
        help_text="YouTube video or live stream URL"
    )
    date = models.DateTimeField(help_text="Date and time of the live stream")
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the live stream"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        help_text="Current status of the live stream"
    )
    
    # Additional useful fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Extracted YouTube video ID for easier embedding
    youtube_video_id = models.CharField(
        max_length=20,
        blank=True,
        help_text="Auto-extracted YouTube video ID"
    )
    
    class Meta:
        ordering = ['-date']
        verbose_name = "Live Video"
        verbose_name_plural = "Live Videos"
    
    def __str__(self):
        return f"{self.lottery_name} - {self.date.strftime('%Y-%m-%d %H:%M')}"
    
    def clean(self):
        """Validate YouTube URL and extract video ID"""
        if self.youtube_url:
            video_id = self.extract_youtube_id(self.youtube_url)
            self.youtube_video_id = video_id or ""  # Set to empty string if None
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @staticmethod
    def extract_youtube_id(url):
        """Extract YouTube video ID from various YouTube URL formats"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/live\/([^&\n?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    @property
    def embed_url(self):
        """Generate YouTube embed URL"""
        if self.youtube_video_id:
            return f"https://www.youtube.com/embed/{self.youtube_video_id}"
        return None
    
    @property
    def is_live_now(self):
        """Check if the stream is currently live"""
        from django.utils import timezone
        return (
            self.status == 'live' and 
            self.date <= timezone.now() and 
            self.is_active
        )
    
#<-----------------------NOTIFICATION SECTION---------------->
class FcmToken(models.Model):
    """Simple model to store FCM tokens for push notifications"""
    
    phone_number = models.CharField(max_length=15, db_index=True)
    name = models.CharField(max_length=100)
    fcm_token = models.TextField(unique=True)
    notifications_enabled = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'fcm_tokens'
    
    def __str__(self):
        return f"{self.name} ({self.phone_number})"
    

# Add this to the end of your models.py file
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

@receiver(pre_save, sender=LotteryResult)
def lottery_result_pre_save_handler(sender, instance, **kwargs):
    """
    Store the original published state before save
    """
    if instance.pk:
        try:
            old_instance = LotteryResult.objects.get(pk=instance.pk)
            instance._original_published = old_instance.is_published
            instance._original_results_ready = old_instance.results_ready_notification
        except LotteryResult.DoesNotExist:
            instance._original_published = False
            instance._original_results_ready = False
    else:
        instance._original_published = False
        instance._original_results_ready = False

@receiver(post_save, sender=LotteryResult)
def lottery_result_notification_handler(sender, instance, created, **kwargs):
    """
    Automatically send notifications when lottery results are published
    """
    try:
        from .services.fcm_service import FCMService
        import logging
        
        logger = logging.getLogger('lottery_app')
        
        if created:
            # New result created - send notification only if published
            if instance.is_published:
                logger.info(f"📱 New lottery result created and published: {instance.lottery.name}")
                result = FCMService.send_new_result_notification(
                    lottery_name=instance.lottery.name
                )
                logger.info(f"📤 New result notification sent: {result}")
        else:
            # Existing result updated - check if is_published changed from False to True
            if (hasattr(instance, '_original_published') and 
                not instance._original_published and 
                instance.is_published):
                
                logger.info(f"📱 Lottery result published (False→True): {instance.lottery.name}")
                result = FCMService.send_new_result_notification(
                    lottery_name=instance.lottery.name
                )
                logger.info(f"📤 Publication notification sent: {result}")
        
        # Handle results_ready_notification independently
        if hasattr(instance, '_original_results_ready'):
            if (instance.results_ready_notification and 
                not instance._original_results_ready and
                not instance.notification_sent):
                
                # Checkbox was just checked - send notification
                logger.info(f"📱 Results ready notification triggered: {instance.lottery.name}")
                result = FCMService.send_result_ready_notification(
                    lottery_name=instance.lottery.name,
                    draw_number=instance.draw_number
                )
                logger.info(f"📤 Results ready notification sent: {result}")
                
                # Mark notification as sent
                instance.notification_sent = True
                instance.save(update_fields=['notification_sent'])
                
            elif (not instance.results_ready_notification and 
                  instance._original_results_ready and
                  instance.notification_sent):
                
                # Checkbox was just unchecked - reset notification_sent
                logger.info(f"🔄 Results ready notification reset: {instance.lottery.name}")
                instance.notification_sent = False
                instance.save(update_fields=['notification_sent'])
            
    except Exception as e:
        logger.error(f"❌ Error in lottery notification handler: {e}")


#<---------------------POINTS SECTION--------------------->
# Add these models to your existing models.py file

class DailyPointsPool(models.Model):
    """Manages daily points pool with 10K budget that resets at midnight IST"""
    date = models.DateField(unique=True, db_index=True)
    total_budget = models.IntegerField(default=10000)
    distributed_points = models.IntegerField(default=0)
    remaining_points = models.IntegerField(default=10000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Daily Points Pool"
        verbose_name_plural = "Daily Points Pools"
        ordering = ['-date']
    
    def __str__(self):
        return f"Pool {self.date}: {self.remaining_points}/{self.total_budget} remaining"
    
    @classmethod
    def get_today_pool(cls):
        """Get or create today's points pool (IST timezone)"""
        ist = pytz.timezone('Asia/Kolkata')
        today_ist = timezone.now().astimezone(ist).date()
        
        pool, created = cls.objects.get_or_create(
            date=today_ist,
            defaults={
                'total_budget': 10000,
                'distributed_points': 0,
                'remaining_points': 10000
            }
        )
        return pool
    
    def can_award_points(self, points_amount):
        """Check if pool has enough points to award"""
        return self.remaining_points >= points_amount
    
    def award_points(self, points_amount):
        """Award points and update pool (with database transaction)"""
        with transaction.atomic():
            # Refresh from database to prevent race conditions
            pool = DailyPointsPool.objects.select_for_update().get(id=self.id)
            
            if pool.remaining_points >= points_amount:
                pool.distributed_points += points_amount
                pool.remaining_points -= points_amount
                pool.save(update_fields=['distributed_points', 'remaining_points', 'updated_at'])
                return True
            return False


class UserPointsBalance(models.Model):
    """Track total points balance for each user (phone number)"""
    phone_number = models.CharField(max_length=15, unique=True, db_index=True)
    total_points = models.IntegerField(default=0)
    lifetime_earned = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Points Balance"
        verbose_name_plural = "User Points Balances"
    
    def __str__(self):
        return f"{self.phone_number}: {self.total_points} points"
    
    @classmethod
    def get_or_create_user(cls, phone_number):
        """Get or create user balance record"""
        user, created = cls.objects.get_or_create(
            phone_number=phone_number,
            defaults={'total_points': 0, 'lifetime_earned': 0}
        )
        return user
    
    def add_points(self, points_amount):
        """Add points to user balance"""
        self.total_points += points_amount
        self.lifetime_earned += points_amount
        self.save(update_fields=['total_points', 'lifetime_earned', 'updated_at'])


class PointsTransaction(models.Model):
    """Track all points transactions for audit and user history"""
    TRANSACTION_TYPES = [
        ('lottery_check', 'Lottery Check Reward'),
        ('bonus', 'Bonus Points'),
        ('redemption', 'Points Redemption'),
        ('adjustment', 'Manual Adjustment'),
    ]
    
    phone_number = models.CharField(max_length=15, db_index=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    points_amount = models.IntegerField()
    balance_before = models.IntegerField()
    balance_after = models.IntegerField()
    
    # Lottery check specific fields
    ticket_number = models.CharField(max_length=50, blank=True)
    lottery_name = models.CharField(max_length=200, blank=True)
    check_date = models.DateField(null=True, blank=True)
    
    # Pool tracking
    daily_pool_date = models.DateField(null=True, blank=True)
    
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Points Transaction"
        verbose_name_plural = "Points Transactions"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', '-created_at']),
            models.Index(fields=['daily_pool_date']),
        ]
    
    def __str__(self):
        return f"{self.phone_number}: {self.points_amount} pts ({self.get_transaction_type_display()})"


class DailyPointsAwarded(models.Model):
    """Track which users have received points today (prevents multiple awards per day)"""
    phone_number = models.CharField(max_length=15, db_index=True)
    award_date = models.DateField(db_index=True)
    points_awarded = models.IntegerField()
    ticket_number = models.CharField(max_length=50)
    lottery_name = models.CharField(max_length=200)
    awarded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Daily Points Awarded"
        verbose_name_plural = "Daily Points Awarded"
        unique_together = ('phone_number', 'award_date')  # One award per user per day
        ordering = ['-award_date', '-awarded_at']
    
    def __str__(self):
        return f"{self.phone_number}: {self.points_awarded} pts on {self.award_date}"
    
    @classmethod
    def has_received_points_today(cls, phone_number):
        """Check if user has already received points today (IST)"""
        ist = pytz.timezone('Asia/Kolkata')
        today_ist = timezone.now().astimezone(ist).date()
        
        return cls.objects.filter(
            phone_number=phone_number,
            award_date=today_ist
        ).exists()
    
    @classmethod
    def record_points_award(cls, phone_number, points_amount, ticket_number, lottery_name):
        """Record that user received points today"""
        ist = pytz.timezone('Asia/Kolkata')
        today_ist = timezone.now().astimezone(ist).date()
        
        return cls.objects.create(
            phone_number=phone_number,
            award_date=today_ist,
            points_awarded=points_amount,
            ticket_number=ticket_number,
            lottery_name=lottery_name
        )