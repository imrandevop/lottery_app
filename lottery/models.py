from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

class LotteryType(models.Model):
    name = models.CharField(max_length=100)  # e.g., "Akshaya", "Win Win"
    code = models.CharField(max_length=20)   # e.g., "AK", "WW"
    price = models.IntegerField()            # Price in rupees
    first_prize_amount = models.IntegerField()  # Amount in rupees
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class LotteryDraw(models.Model):
    lottery_type = models.ForeignKey(LotteryType, on_delete=models.CASCADE, related_name='draws')
    draw_number = models.IntegerField()  # e.g., 620 for "Akshaya AK 620"
    draw_date = models.DateField()
    result_declared = models.BooleanField(default=False)
    is_new = models.BooleanField(default=True)  # To show "NEW" tag in frontend
    
    class Meta:
        unique_together = ('lottery_type', 'draw_number')
        ordering = ['-draw_date', '-draw_number']
    
    def __str__(self):
        return f"{self.lottery_type.name} {self.lottery_type.code} {self.draw_number}"
    
    @property
    def is_today(self):
        return self.draw_date == timezone.now().date()
    
    @property
    def is_yesterday(self):
        return self.draw_date == (timezone.now().date() - timezone.timedelta(days=1))
    
    @property
    def full_name(self):
        return f"{self.lottery_type.name} {self.lottery_type.code} {self.draw_number}"

class PrizeCategory(models.Model):
    name = models.CharField(max_length=100)  # e.g., "1st Prize", "Consolation Prize"
    display_name = models.CharField(max_length=100, blank=True)  # e.g., "1st Prize Rs 700000/- [70 Lakhs]"
    amount = models.IntegerField()  # Prize amount in rupees
    display_amount = models.CharField(max_length=50, blank=True)  # Formatted amount with lakhs, etc.
    lottery_type = models.ForeignKey(LotteryType, on_delete=models.CASCADE, related_name='prize_categories', null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # Auto-format display amount if not provided
        if not self.display_amount and self.amount:
            lakhs = self.amount / 100000
            if lakhs >= 1:
                self.display_amount = f"Rs {self.amount}/- [{int(lakhs)} Lakhs]"
            else:
                self.display_amount = f"Rs {self.amount}/-"
        
        # Auto-format display name if not provided
        if not self.display_name and self.name:
            if "1st" in self.name or "First" in self.name:
                self.display_name = f"1st Prize {self.display_amount}"
            else:
                self.display_name = f"{self.name} {self.display_amount}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        lottery_info = f" ({self.lottery_type.code})" if self.lottery_type else ""
        return f"{self.name}{lottery_info} ({self.amount} Rs)"
    
    class Meta:
        verbose_name = "Prize Category"
        verbose_name_plural = "Prize Categories"

class WinningTicket(models.Model):
    draw = models.ForeignKey(LotteryDraw, on_delete=models.CASCADE, related_name='winners')
    series = models.CharField(max_length=10)  # e.g., "AY", "NB", etc.
    number = models.CharField(max_length=10)  # Winning number
    prize_category = models.ForeignKey(PrizeCategory, on_delete=models.CASCADE, related_name='winning_tickets')
    location = models.CharField(max_length=100, blank=True, null=True)  # e.g., "Thrissur"
    
    class Meta:
        ordering = ['prize_category']
    
    def __str__(self):
        return f"{self.series} {self.number} - {self.prize_category.name}"
    
    @property
    def full_number(self):
        return f"{self.series} {self.number}"


@receiver(pre_save, sender=LotteryDraw)
def set_lottery_draw_defaults(sender, instance, **kwargs):
    """Set default values for a new lottery draw"""
    # If this is an existing object, get the old instance
    try:
        old_instance = LotteryDraw.objects.get(pk=instance.pk)
        # If lottery type has changed, clear related winners
        if old_instance.lottery_type != instance.lottery_type:
            # This will delete existing winning tickets when lottery type changes
            # Comment out this line if you don't want this behavior
            instance.winners.all().delete()
    except LotteryDraw.DoesNotExist:
        # This is a new object, nothing to do
        pass