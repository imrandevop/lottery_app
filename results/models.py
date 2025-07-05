from django.db import models
import uuid
from django.utils import timezone


class Lottery(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    first_price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Lottery"
        verbose_name_plural = "Lotteries"


class LotteryResult(models.Model):
    # Unique UUID field
    unique_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Basic Information
    lottery = models.ForeignKey(Lottery, on_delete=models.CASCADE)
    date = models.DateField()
    draw_number = models.CharField(max_length=50)
    is_published = models.BooleanField(default=False, verbose_name="Published")
    is_bumper = models.BooleanField(default=False, verbose_name="Bumper")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.lottery.name} - Draw {self.draw_number} - {self.date}"
    
    class Meta:
        verbose_name = "Add Result"
        verbose_name_plural = "Add Results"
        unique_together = ['lottery', 'draw_number', 'date']


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
    """Store prediction history for performance tracking"""
    lottery_name = models.CharField(max_length=200)
    prize_type = models.CharField(max_length=20)
    predicted_numbers = models.JSONField()
    actual_numbers = models.JSONField(null=True, blank=True)
    prediction_date = models.DateTimeField(auto_now_add=True)
    draw_date = models.DateField(null=True, blank=True)
    accuracy_score = models.FloatField(null=True, blank=True)
    model_used = models.ForeignKey(PredictionModel, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"{self.lottery_name} - {self.prize_type} - {self.prediction_date.date()}"

