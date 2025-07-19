from django.db import models
import uuid
from django.utils import timezone
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import re
import pytz


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

@receiver(post_save, sender=LotteryResult)
def lottery_result_notification_handler(sender, instance, created, **kwargs):
    """
    Automatically send notifications when lottery results are published
    """
    try:
        from .services.fcm_service import FCMService
        import logging
        
        logger = logging.getLogger('lottery_app')
        
        # Only send notifications for published results
        if not instance.is_published:
            return
        
        # Check if this is a newly published result or an update
        if created:
            # New result added and published
            logger.info(f"📱 New lottery result created: {instance.lottery.name}")
            result = FCMService.send_new_result_notification(
                lottery_name=instance.lottery.name
            )
            logger.info(f"📤 New result notification sent: {result}")
            
        else:
            # Existing result updated - check if it was just published
            try:
                # Get the previous state from database
                old_instance = LotteryResult.objects.get(pk=instance.pk)
                
                # If it wasn't published before but is now published
                if not hasattr(old_instance, '_original_published'):
                    # We'll handle this with pre_save signal
                    pass
                    
            except LotteryResult.DoesNotExist:
                pass
        
        # Check if results_ready_notification checkbox was ticked
        if instance.results_ready_notification and not instance.notification_sent:
            logger.info(f"📱 Results ready notification triggered: {instance.lottery.name}")
            result = FCMService.send_result_ready_notification(
                lottery_name=instance.lottery.name,
                draw_number=instance.draw_number
            )
            logger.info(f"📤 Results ready notification sent: {result}")
            
            # Mark notification as sent to avoid duplicates
            instance.notification_sent = True
            instance.save(update_fields=['notification_sent'])
            
    except Exception as e:
        logger.error(f"❌ Error in lottery notification handler: {e}")

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


