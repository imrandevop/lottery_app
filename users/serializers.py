from rest_framework import serializers
from .models import User, LotteryPurchase
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


class LotteryPurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = LotteryPurchase
        fields = ['user_id', 'lottery_number', 'lottery_name', 'ticket_price', 'purchase_date', 'lottery_unique_id']

    def validate_user_id(self, value):
        try:
            User.objects.get(phone_number=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")
        return value

    def validate(self, data):
        # Check for duplicate entry
        existing = LotteryPurchase.objects.filter(
            user_id=data['user_id'],
            lottery_number=data['lottery_number'],
            purchase_date=data['purchase_date']
        ).exists()

        if existing:
            raise serializers.ValidationError("Lottery entry already exists for this user, number, and date.")

        return data


class LotteryStatisticsSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=20)

    def validate_user_id(self, value):
        try:
            User.objects.get(phone_number=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")
        return value

