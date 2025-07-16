from rest_framework import serializers
from .models import User
from django.contrib.auth import get_user_model
User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['phone_number', 'name']
    
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class UserLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    
    def validate_phone_number(self, value):
        try:
            User.objects.get(phone_number=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this phone number.")
        return value
    
#<---------------------NOTIFICATIONS SECTION--------------------->

class FCMTokenSerializer(serializers.Serializer):
    """
    Serializer for FCM token registration
    """
    fcm_token = serializers.CharField(max_length=1000, required=True)
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notifications_enabled = serializers.BooleanField(default=True)
    
    def validate_fcm_token(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("FCM token cannot be empty")
        return value.strip()
    
    def validate_phone_number(self, value):
        if value and not value.strip():
            return None
        return value.strip() if value else None

class UserNotificationPreferencesSerializer(serializers.ModelSerializer):
    """
    Serializer for user notification preferences
    """
    class Meta:
        model = User
        fields = ['notifications_enabled', 'fcm_token_updated_at']
        read_only_fields = ['fcm_token_updated_at']

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration with FCM token
    """
    fcm_token = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['phone_number', 'name', 'fcm_token', 'notifications_enabled']
        
    def create(self, validated_data):
        fcm_token = validated_data.pop('fcm_token', None)
        user = User.objects.create_user(**validated_data)
        
        if fcm_token:
            user.fcm_token = fcm_token
            user.save()
            
        return user