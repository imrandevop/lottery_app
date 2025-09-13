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
    

# IMPORTANT: LotteryResult signal handlers have been moved to signals.py
# to prevent duplicate signal registration and infinite loops.
# All notification and cache logic is now consolidated in signals.py

# Import signals for remaining handlers
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


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
    
#<---------------------CASH BACK SECTION--------------------->

class DailyCashPool(models.Model):
    """Manages daily cash pool with ₹100 budget for first 30 eligible users"""
    date = models.DateField(unique=True, db_index=True)
    total_budget = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)
    distributed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)
    users_awarded = models.IntegerField(default=0)  # Track number of users who got cash back
    max_users = models.IntegerField(default=30)     # Maximum 30 users per day
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Daily Cash Pool"
        verbose_name_plural = "Daily Cash Pools"
        ordering = ['-date']
    
    def __str__(self):
        return f"Cash Pool {self.date}: ₹{self.remaining_amount}/{self.total_budget} remaining ({self.users_awarded}/{self.max_users} users)"
    
    @classmethod
    def get_today_pool(cls):
        """Get or create today's cash pool (IST timezone)"""
        ist = pytz.timezone('Asia/Kolkata')
        today_ist = timezone.now().astimezone(ist).date()
        
        pool, created = cls.objects.get_or_create(
            date=today_ist,
            defaults={
                'total_budget': 100.00,
                'distributed_amount': 0.00,
                'remaining_amount': 100.00,
                'users_awarded': 0,
                'max_users': 30
            }
        )
        return pool
    
    def can_award_cash(self, cash_amount):
        """Check if pool can award cash (has budget and user slots)"""
        return (self.remaining_amount >= cash_amount and 
                self.users_awarded < self.max_users)
    
    def award_cash(self, cash_amount):
        """Award cash and update pool (with database transaction)"""
        with transaction.atomic():
            # Refresh from database to prevent race conditions
            pool = DailyCashPool.objects.select_for_update().get(id=self.id)
            
            if pool.can_award_cash(cash_amount):
                pool.distributed_amount += cash_amount
                pool.remaining_amount -= cash_amount
                pool.users_awarded += 1
                pool.save(update_fields=['distributed_amount', 'remaining_amount', 'users_awarded', 'updated_at'])
                return True
            return False


class UserCashBalance(models.Model):
    """Track total cash balance for each user (phone number)"""
    phone_number = models.CharField(max_length=15, unique=True, db_index=True)
    total_cash = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cash_withdrawn = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Total amount withdrawn by user")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Cash Balance"
        verbose_name_plural = "User Cash Balances"
    
    def __str__(self):
        return f"{self.phone_number}: ₹{self.total_cash}"
    
    @classmethod
    def get_or_create_user(cls, phone_number):
        """Get or create user cash balance record"""
        user, created = cls.objects.get_or_create(
            phone_number=phone_number,
            defaults={'total_cash': 0.00, 'cash_withdrawn': 0.00}
        )
        return user
    
    def add_cash(self, cash_amount):
        """Add cash to user balance"""
        self.total_cash += cash_amount
        # Note: cash_withdrawn will be updated via signal when admin marks as claimed
        self.save(update_fields=['total_cash', 'updated_at'])
    
    def add_withdrawal(self, amount):
        """Add to cash withdrawn amount (called by signal)"""
        self.cash_withdrawn += amount
        self.save(update_fields=['cash_withdrawn', 'updated_at'])
    
    def subtract_withdrawal(self, amount):
        """Subtract from cash withdrawn amount (called by signal when unclaimed)"""
        self.cash_withdrawn = max(0, self.cash_withdrawn - amount)
        self.save(update_fields=['cash_withdrawn', 'updated_at'])


class CashTransaction(models.Model):
    """Track all cash transactions for audit and user history"""
    TRANSACTION_TYPES = [
        ('lottery_check', 'Lottery Check Cash Back'),
        ('bonus', 'Bonus Cash'),
        ('redemption', 'Cash Redemption'),
        ('adjustment', 'Manual Adjustment'),
    ]
    
    phone_number = models.CharField(max_length=15, db_index=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    cash_amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_before = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Lottery check specific fields
    ticket_number = models.CharField(max_length=50, blank=True)
    lottery_name = models.CharField(max_length=200, blank=True)
    check_date = models.DateField(null=True, blank=True)
    
    # Pool tracking
    daily_cash_pool_date = models.DateField(null=True, blank=True)
    
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Cash Transaction"
        verbose_name_plural = "Cash Transactions"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', '-created_at']),
            models.Index(fields=['daily_cash_pool_date']),
        ]
    
    def __str__(self):
        return f"{self.phone_number}: ₹{self.cash_amount} ({self.get_transaction_type_display()})"


class DailyCashAwarded(models.Model):
    """Track which users have received cash back today (prevents multiple awards per day)"""
    phone_number = models.CharField(max_length=15, db_index=True)
    award_date = models.DateField(db_index=True)
    cash_awarded = models.DecimalField(max_digits=10, decimal_places=2)
    ticket_number = models.CharField(max_length=50)
    lottery_name = models.CharField(max_length=200)
    awarded_at = models.DateTimeField(auto_now_add=True)
    
    # New fields for cashback management
    cashback_id = models.CharField(max_length=20, unique=True, blank=True, help_text="Auto-generated cashback ID")
    is_claimed = models.BooleanField(default=False, help_text="Whether the cashback has been claimed by user")
    
    class Meta:
        verbose_name = "Daily Cash Awarded"
        verbose_name_plural = "Daily Cash Awarded"
        unique_together = ('phone_number', 'award_date')  # One award per user per day
        ordering = ['-award_date', '-awarded_at']
    
    def __str__(self):
        claim_status = "✅ Claimed" if self.is_claimed else "⏳ Pending"
        return f"{self.cashback_id or 'No ID'}: ₹{self.cash_awarded} - {claim_status}"
    
    def save(self, *args, **kwargs):
        """Auto-generate cashback_id if not provided"""
        if not self.cashback_id:
            # Generate cashback ID format: CB + YYYYMMDD + sequential number (CB20250825001)
            ist = pytz.timezone('Asia/Kolkata')
            date_str = self.award_date.strftime('%Y%m%d') if self.award_date else timezone.now().astimezone(ist).strftime('%Y%m%d')
            
            # Get the count of cashback entries for this date to generate sequential number
            date_count = DailyCashAwarded.objects.filter(
                award_date=self.award_date or timezone.now().astimezone(ist).date()
            ).count()
            
            # Format: CB + YYYYMMDD + 3-digit sequential number
            self.cashback_id = f"CB{date_str}{(date_count + 1):03d}"
        
        super().save(*args, **kwargs)
    
    @classmethod
    def has_received_cash_today(cls, phone_number):
        """Check if user has already received cash back today (IST)"""
        try:
            ist = pytz.timezone('Asia/Kolkata')
            today_ist = timezone.now().astimezone(ist).date()
            
            return cls.objects.filter(
                phone_number=phone_number,
                award_date=today_ist
            ).exists()
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error in has_received_cash_today: {e}")
            return False
    
    @classmethod
    def record_cash_award(cls, phone_number, cash_amount, ticket_number, lottery_name):
        """Record that user received cash back today"""
        try:
            ist = pytz.timezone('Asia/Kolkata')
            today_ist = timezone.now().astimezone(ist).date()
            
            return cls.objects.create(
                phone_number=phone_number,
                award_date=today_ist,
                cash_awarded=cash_amount,
                ticket_number=ticket_number,
                lottery_name=lottery_name
            )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error in record_cash_award: {e}")
            raise e


#<---------------------CASH WITHDRAWAL SIGNALS--------------------->
# Signals for DailyCashAwarded to update UserCashBalance.cash_withdrawn

@receiver(pre_save, sender=DailyCashAwarded)
def daily_cash_awarded_pre_save_handler(sender, instance, **kwargs):
    """
    Store the original claimed state before save
    """
    if instance.pk:
        try:
            old_instance = DailyCashAwarded.objects.get(pk=instance.pk)
            instance._original_is_claimed = old_instance.is_claimed
        except DailyCashAwarded.DoesNotExist:
            instance._original_is_claimed = False
    else:
        instance._original_is_claimed = False


@receiver(post_save, sender=DailyCashAwarded)
def daily_cash_awarded_post_save_handler(sender, instance, created, **kwargs):
    """
    Update UserCashBalance.cash_withdrawn when is_claimed status changes
    """
    try:
        import logging
        logger = logging.getLogger('lottery_app')
        
        # Skip if this is a new record creation (no claim status change)
        if created:
            return
        
        # Check if is_claimed status changed
        if hasattr(instance, '_original_is_claimed'):
            original_claimed = instance._original_is_claimed
            current_claimed = instance.is_claimed
            
            # If claim status changed
            if original_claimed != current_claimed:
                # Get or create user cash balance
                user_balance = UserCashBalance.get_or_create_user(instance.phone_number)
                
                if current_claimed and not original_claimed:
                    # Changed from unclaimed to claimed - add to cash_withdrawn
                    user_balance.add_withdrawal(instance.cash_awarded)
                    logger.info(f"CASH CLAIMED: Added Rs{instance.cash_awarded} to cash_withdrawn for {instance.phone_number} (ID: {instance.cashback_id})")
                    
                elif not current_claimed and original_claimed:
                    # Changed from claimed to unclaimed - subtract from cash_withdrawn
                    user_balance.subtract_withdrawal(instance.cash_awarded)
                    logger.info(f"CASH UNCLAIMED: Subtracted Rs{instance.cash_awarded} from cash_withdrawn for {instance.phone_number} (ID: {instance.cashback_id})")
                
    except Exception as e:
        logger.error(f"❌ Error in cash withdrawal signal handler: {e}")


class PeoplesPrediction(models.Model):
    """
    Model to store peoples' single digit predictions
    Data auto-deletes after 1 day (3:00 PM to next day 3:00 PM)
    """
    peoples_prediction = models.CharField(max_length=1, help_text="Single digit prediction (0-9)")
    user_ip = models.GenericIPAddressField(null=True, blank=True, help_text="User IP address for tracking")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "People's Prediction"
        verbose_name_plural = "People's Predictions"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Prediction: {self.peoples_prediction} at {self.created_at}"
    
    @classmethod
    def cleanup_old_predictions(cls):
        """
        Remove predictions older than 1 day (3:00 PM to next day 3:00 PM cycle)
        """
        from datetime import datetime, timedelta, time
        import pytz
        
        india_tz = pytz.timezone('Asia/Kolkata')
        current_datetime = timezone.now().astimezone(india_tz)
        current_date = current_datetime.date()
        current_time = current_datetime.time()
        
        # Calculate the cutoff datetime (yesterday 3:00 PM)
        if current_time >= time(15, 0):  # After 3:00 PM today
            cutoff_date = current_date
        else:  # Before 3:00 PM today
            cutoff_date = current_date - timedelta(days=1)
        
        cutoff_datetime = datetime.combine(cutoff_date, time(15, 0))
        cutoff_datetime = india_tz.localize(cutoff_datetime)
        
        # Delete old predictions
        deleted_count = cls.objects.filter(created_at__lt=cutoff_datetime).count()
        cls.objects.filter(created_at__lt=cutoff_datetime).delete()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old people's predictions")
        
        return deleted_count