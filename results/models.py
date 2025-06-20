from django.db import models
import uuid


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
        max_length=500, 
        verbose_name="Update Image 1 URL",
        help_text="URL for the first update image"
    )
    update_image2 = models.URLField(
        max_length=500, 
        verbose_name="Update Image 2 URL",
        help_text="URL for the second update image"
    )
    update_image3 = models.URLField(
        max_length=500, 
        verbose_name="Update Image 3 URL",
        help_text="URL for the third update image"
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
    
    # Remove the singleton save() method override
    # def save(self, *args, **kwargs):
    #     if not self.pk and ImageUpdate.objects.exists():
    #         raise ValueError("Only one ImageUpdate instance is allowed.")
    #     super().save(*args, **kwargs)
    
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
            )
        
        return latest_instance