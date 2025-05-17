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

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=50, unique=True, null=True, blank=True)  # Allow null temporarily
    phone_number = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=100)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    
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