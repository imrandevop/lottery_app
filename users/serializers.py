from rest_framework import serializers
from .models import User, LotteryPurchase, Feedback
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
    is_deleted = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = LotteryPurchase
        fields = ['id', 'user_id', 'lottery_number', 'lottery_name', 'ticket_price', 'purchase_date', 'lottery_unique_id', 'is_deleted']
        extra_kwargs = {
            'lottery_number': {'required': False},
            'lottery_name': {'required': False},
            'ticket_price': {'required': False},
            'purchase_date': {'required': False},
        }

    def validate_user_id(self, value):
        try:
            User.objects.get(phone_number=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")
        return value

    def validate(self, data):
        is_deleted = data.get('is_deleted', False)
        record_id = data.get('id')

        # If delete operation
        if is_deleted:
            if not record_id:
                raise serializers.ValidationError("ID is required for delete operation.")
            return data

        # For create operation - validate required fields
        if not record_id:  # Creating new record
            required_fields = ['lottery_number', 'lottery_name', 'ticket_price', 'purchase_date']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError(f"{field} is required for create operation.")

            # Check for duplicate entry
            existing = LotteryPurchase.objects.filter(
                user_id=data['user_id'],
                lottery_number=data['lottery_number'],
                purchase_date=data['purchase_date']
            ).exists()

            if existing:
                raise serializers.ValidationError("Lottery entry already exists for this user, number, and date.")

        return data

    def run_validation(self, data=serializers.empty):
        # If it's a delete operation, skip model validation
        if data != serializers.empty and data.get('is_deleted', False):
            # For delete, only validate user_id and id fields manually
            user_id = data.get('user_id')
            record_id = data.get('id')

            if not user_id:
                raise serializers.ValidationError({'user_id': ['This field is required.']})
            if not record_id:
                raise serializers.ValidationError({'id': ['ID is required for delete operation.']})

            # Validate user exists
            try:
                User.objects.get(phone_number=user_id)
            except User.DoesNotExist:
                raise serializers.ValidationError({'user_id': ['User does not exist.']})

            return data

        # For create operation, use normal validation
        return super().run_validation(data)

    def create(self, validated_data):
        # Remove non-model fields before creating
        validated_data.pop('is_deleted', None)
        return super().create(validated_data)


class LotteryStatisticsSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=20)

    def validate_user_id(self, value):
        try:
            User.objects.get(phone_number=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")
        return value


class FeedbackSerializer(serializers.ModelSerializer):
	class Meta:
		model = Feedback
		fields = ['phone_number', 'screen_name', 'message']

