# users\models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class UserManager(BaseUserManager):
    def create_user(self, phone_number, name, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number field must be set')
        
        # Generate a username from phone number if not provided
        if not extra_fields.get('username'):
            extra_fields['username'] = f"user_{phone_number}"
        
        user = self.model(
            phone_number=phone_number,
            name=name,
            **extra_fields
        )
        
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone_number, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if not extra_fields.get('username'):
            extra_fields['username'] = f"admin_{phone_number}"
            
        if password is None:
            raise ValueError('Superuser must have a password')
            
        return self.create_user(phone_number, name, password, **extra_fields)

# Add these fields to your existing User model in users/models.py

# Update your existing User class by adding these fields:

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=50, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=100)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    # FCM Token for push notifications
    fcm_token = models.TextField(
        blank=True, 
        null=True, 
        help_text="Firebase Cloud Messaging token for push notifications"
    )
    
    # Notification preferences
    notifications_enabled = models.BooleanField(
        default=True, 
        help_text="Whether user wants to receive push notifications"
    )
    
    # Track when token was last updated
    fcm_token_updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When FCM token was last updated"
    )
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['phone_number', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.phone_number})"
    
    def save(self, *args, **kwargs):
        # Auto-generate username if not provided
        if not self.username:
            self.username = f"user_{self.phone_number}"
        super().save(*args, **kwargs)


class LotteryPurchase(models.Model):
    user_id = models.CharField(max_length=20, help_text="User identifier")
    lottery_number = models.CharField(max_length=10, help_text="Lottery ticket number")
    lottery_name = models.CharField(max_length=100, help_text="Name of the lottery")
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price of the lottery ticket")
    purchase_date = models.DateField(help_text="Date of purchase")
    lottery_unique_id = models.UUIDField(null=True, blank=True, help_text="Lottery result unique ID for checking wins")
    winnings = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Prize amount if won")
    is_winner = models.BooleanField(default=False, help_text="Whether this ticket won any prize")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user_id', 'lottery_number', 'purchase_date']
        ordering = ['-purchase_date', '-created_at']

    def __str__(self):
        return f"{self.user_id} - {self.lottery_name} ({self.lottery_number})"

    def check_win_status(self):
        """Check if this ticket won based on lottery results"""
        if not self.lottery_unique_id:
            return "pending"

        try:
            from results.models import LotteryResult, PrizeEntry

            # Get the lottery result
            lottery_result = LotteryResult.objects.get(
                unique_id=self.lottery_unique_id,
                is_published=True
            )

            # Check if ticket won any prize
            last_4_digits = self.lottery_number[-4:] if len(self.lottery_number) >= 4 else self.lottery_number

            # Check full ticket match
            full_match = PrizeEntry.objects.filter(
                ticket_number=self.lottery_number,
                lottery_result=lottery_result
            ).first()

            # Check last 4 digits match
            partial_match = PrizeEntry.objects.filter(
                ticket_number=last_4_digits,
                lottery_result=lottery_result
            ).exclude(ticket_number=self.lottery_number).first()

            winning_prize = full_match or partial_match

            if winning_prize:
                # Update winning status
                self.is_winner = True
                self.winnings = winning_prize.prize_amount
                self.save(update_fields=['is_winner', 'winnings'])
                return "won"
            else:
                # Not a winner
                self.is_winner = False
                self.winnings = None
                self.save(update_fields=['is_winner', 'winnings'])
                return "lost"

        except:
            # Result not found or not published yet
            return "pending"