# models.py (path: lottery/models.py)
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

class LotteryType(models.Model):
    name = models.CharField(max_length=100)  # e.g., "SUVARNA KERALAM"
    code = models.CharField(max_length=20)   # e.g., "SK"
    price = models.IntegerField()            # Price in rupees
    first_prize_amount = models.IntegerField()  # Amount in rupees
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    class Meta:
        verbose_name = "Lottery"
        verbose_name_plural = "Lotteries"

class LotteryDraw(models.Model):
    lottery_type = models.ForeignKey(LotteryType, on_delete=models.CASCADE, related_name='draws')
    draw_number = models.IntegerField()
    draw_date = models.DateField()
    result_declared = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('lottery_type', 'draw_number')
        ordering = ['-draw_date', '-draw_number']
        verbose_name = "Lottery Draw"
        verbose_name_plural = "Lottery Draws"
    
    def __str__(self):
        return f"{self.lottery_type.name} {self.lottery_type.code}-{self.draw_number}"
    
    @property
    def draw_code(self):
        return f"{self.lottery_type.code}-{self.draw_number}"
    
    @property
    def is_today(self):
        return self.draw_date == timezone.now().date()
    
    @property
    def is_yesterday(self):
        return self.draw_date == (timezone.now().date() - timezone.timedelta(days=1))
    
    @property
    def full_name(self):
        return f"{self.lottery_type.name} {self.lottery_type.code}-{self.draw_number}"

# First Prize (Separate model for 1st prize with location)
class FirstPrize(models.Model):
    draw = models.OneToOneField(LotteryDraw, on_delete=models.CASCADE, related_name='first_prize')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=10000000.00)  # ₹1,00,00,000/-
    ticket_number = models.CharField(max_length=20)  # e.g., "RL528610"
    place = models.CharField(max_length=100)  # e.g., "GURUVAYOOR"
    
    def __str__(self):
        return f"First Prize - {self.ticket_number} - {self.place}"

# Second Prize
class SecondPrize(models.Model):
    draw = models.OneToOneField(LotteryDraw, on_delete=models.CASCADE, related_name='second_prize')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=3000000.00)  # ₹30,00,000/-
    ticket_number = models.CharField(max_length=20)  # e.g., "RH410634"
    place = models.CharField(max_length=100)  # e.g., "THIRUVANANTHAPURAM"
    
    def __str__(self):
        return f"Second Prize - {self.ticket_number} - {self.place}"

# Third Prize
class ThirdPrize(models.Model):
    draw = models.OneToOneField(LotteryDraw, on_delete=models.CASCADE, related_name='third_prize')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=2500000.00)  # ₹25,00,000/-
    ticket_number = models.CharField(max_length=20)  # e.g., "RF227482"
    place = models.CharField(max_length=100)  # e.g., "KOLLAM"
    
    def __str__(self):
        return f"Third Prize - {self.ticket_number} - {self.place}"

# Fourth Prize
class FourthPrize(models.Model):
    draw = models.OneToOneField(LotteryDraw, on_delete=models.CASCADE, related_name='fourth_prize')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=1500000.00)  # ₹15,00,000/-
    ticket_number = models.CharField(max_length=20)  # e.g., "RK401912"
    place = models.CharField(max_length=100)  # e.g., "PALAKKAD"
    
    def __str__(self):
        return f"Fourth Prize - {self.ticket_number} - {self.place}"

# Fifth Prize (Multiple winners)
class FifthPrize(models.Model):
    draw = models.ForeignKey(LotteryDraw, on_delete=models.CASCADE, related_name='fifth_prizes')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=100000.00)  # ₹1,00,000/-
    ticket_number = models.CharField(max_length=20)
    place = models.CharField(max_length=100)
    
    def __str__(self):
        return f"Fifth Prize - {self.ticket_number} - {self.place}"

# Consolation Prize (Same number as 1st prize but different series)
class ConsolationPrize(models.Model):
    draw = models.ForeignKey(LotteryDraw, on_delete=models.CASCADE, related_name='consolation_prizes')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)  # ₹5,000/-
    ticket_number = models.CharField(max_length=20)
    
    def __str__(self):
        return f"Consolation Prize - {self.ticket_number}"

# Sixth Prize (4-digit numbers)
class SixthPrize(models.Model):
    draw = models.ForeignKey(LotteryDraw, on_delete=models.CASCADE, related_name='sixth_prizes')
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=5000.00)  # ₹5,000/-
    number = models.CharField(max_length=4)  # 4-digit numbers
    
    def __str__(self):
        return f"Sixth Prize - {self.number}"

# Seventh Prize (4-digit numbers)
class SeventhPrize(models.Model):
    draw = models.ForeignKey(LotteryDraw, on_delete=models.CASCADE, related_name='seventh_prizes')
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=1000.00)  # ₹1,000/-
    number = models.CharField(max_length=4)  # 4-digit numbers
    
    def __str__(self):
        return f"Seventh Prize - {self.number}"

# Eighth Prize (4-digit numbers)
class EighthPrize(models.Model):
    draw = models.ForeignKey(LotteryDraw, on_delete=models.CASCADE, related_name='eighth_prizes')
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=500.00)  # ₹500/-
    number = models.CharField(max_length=4)  # 4-digit numbers
    
    def __str__(self):
        return f"Eighth Prize - {self.number}"

# Ninth Prize (4-digit numbers)
class NinthPrize(models.Model):
    draw = models.ForeignKey(LotteryDraw, on_delete=models.CASCADE, related_name='ninth_prizes')
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=100.00)  # ₹100/-
    number = models.CharField(max_length=4)  # 4-digit numbers
    
    def __str__(self):
        return f"Ninth Prize - {self.number}"

# Tenth Prize (4-digit numbers)
class TenthPrize(models.Model):
    draw = models.ForeignKey(LotteryDraw, on_delete=models.CASCADE, related_name='tenth_prizes')
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=50.00)  # ₹50/-
    number = models.CharField(max_length=4)  # 4-digit numbers
    
    def __str__(self):
        return f"Tenth Prize - {self.number}"

@receiver(pre_save, sender=LotteryDraw)
def set_lottery_draw_defaults(sender, instance, **kwargs):
    """Set default values for a new lottery draw"""
    # If this is an existing object, get the old instance
    try:
        old_instance = LotteryDraw.objects.get(pk=instance.pk)
        # If lottery type has changed, clear related winners
        if old_instance.lottery_type != instance.lottery_type:
            # This will cascade through all related prizes due to the related_name attribute
            pass
    except LotteryDraw.DoesNotExist:
        # This is a new object, nothing to do
        pass