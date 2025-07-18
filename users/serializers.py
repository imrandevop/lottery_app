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

