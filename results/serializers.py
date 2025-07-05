# serializers.py
from rest_framework import serializers
from .models import Lottery, LotteryResult, PrizeEntry, News, LiveVideo
from collections import defaultdict

class PrizeEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrizeEntry
        fields = ['prize_type', 'prize_amount', 'ticket_number', 'place']

class GroupedPrizeSerializer(serializers.Serializer):
    """Serializer for grouped prizes"""
    prize_type = serializers.CharField()
    prize_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    ticket_numbers = serializers.CharField()
    place = serializers.CharField(allow_null=True, required=False)

class LotteryResultSerializer(serializers.ModelSerializer):
    lottery_name = serializers.CharField(source='lottery.name', read_only=True)
    lottery_code = serializers.CharField(source='lottery.code', read_only=True)
    first_prize = serializers.SerializerMethodField()
    consolation_prizes = serializers.SerializerMethodField()
    
    class Meta:
        model = LotteryResult
        fields = [
            'date',
            'id',
            'unique_id',  # Added unique_id field
            'lottery_name', 
            'lottery_code',
            'draw_number',
            'first_prize',
            'consolation_prizes',
            'is_published',
            'is_bumper'
        ]
    
    def get_first_prize(self, obj):
        """Get first prize details"""
        first_prize = obj.prizes.filter(prize_type='1st').first()
        if first_prize:
            return {
                'amount': first_prize.prize_amount,
                'ticket_number': first_prize.ticket_number,
                'place': first_prize.place
            }
        return None
    
    def get_consolation_prizes(self, obj):
        """Get consolation prizes with amount shown once and ticket numbers grouped"""
        consolation_prizes = obj.prizes.filter(prize_type='consolation')[:6]
        
        if not consolation_prizes:
            return None
        
        # Get the amount (assuming all consolation prizes have the same amount)
        amount = consolation_prizes[0].prize_amount
        
        # Collect all ticket numbers and join them with spaces
        ticket_numbers = ' '.join([prize.ticket_number for prize in consolation_prizes])
        
        return {
            'amount': amount,
            'ticket_numbers': ticket_numbers
        }

class LotteryResultDetailSerializer(serializers.ModelSerializer):
    lottery_name = serializers.CharField(source='lottery.name', read_only=True)
    lottery_code = serializers.CharField(source='lottery.code', read_only=True)
    prizes = serializers.SerializerMethodField()
    
    class Meta:
        model = LotteryResult
        fields = [
            'date',
            'id',
            'unique_id',  # Added unique_id field
            'lottery_name',
            'lottery_code', 
            'draw_number',
            'prizes',
            'is_published',
            'is_bumper',
            'created_at',
            'updated_at'    
        ]
    
    def get_prizes(self, obj):
        """Group prizes by prize_type and prize_amount, with detailed ticket info for certain prizes"""
        # Get all prizes for this lottery result
        all_prizes = obj.prizes.all()
        
        if not all_prizes:
            return []
        
        # Group prizes by (prize_type, prize_amount)
        grouped_prizes = defaultdict(lambda: {'tickets': [], 'places': set()})
        
        for prize in all_prizes:
            # Create a key based on prize_type and prize_amount only
            key = (prize.prize_type, str(prize.prize_amount))
            
            # Store ticket with its location
            ticket_info = {
                'ticket_number': prize.ticket_number,
                'location': prize.place if prize.place else None
            }
            grouped_prizes[key]['tickets'].append(ticket_info)
            
            if prize.place:
                grouped_prizes[key]['places'].add(prize.place)
        
        # Convert grouped data to the desired format
        result = []
        for (prize_type, prize_amount), data in grouped_prizes.items():
            tickets = data['tickets']
            
            # Check if all tickets are 4-digit numbers (grid format)
            is_grid = all(
                ticket['ticket_number'].isdigit() and len(ticket['ticket_number']) == 4 
                for ticket in tickets
            )
            
            prize_data = {
                'prize_type': prize_type,
                'prize_amount': prize_amount,
                'place_used': len(data['places']) > 0,
                'is_grid': is_grid
            }
            
            # For prizes like 3rd that should show detailed ticket info with locations
            if prize_type in ['1st', '2nd', '3rd']:
                prize_data['tickets'] = tickets
            else:
                # For all other prizes including consolation, 4th, 5th, 6th, etc.
                ticket_numbers = ' '.join([ticket['ticket_number'] for ticket in tickets])
                prize_data['ticket_numbers'] = ticket_numbers
            
            result.append(prize_data)

        # Sort results by prize type order
        def prize_sort_key(prize):
            prize_type = prize['prize_type']
            
            # Define custom order: 1st, consolation, 2nd, 3rd, 4th, 5th, etc.
            if prize_type == '1st':
                return (1, prize_type)
            elif prize_type == 'consolation':
                return (2, prize_type)  # Put consolation as 2nd position
            elif prize_type == '2nd':
                return (3, prize_type)
            elif prize_type == '3rd':
                return (4, prize_type)
            elif prize_type.endswith('st') or prize_type.endswith('nd') or prize_type.endswith('rd') or prize_type.endswith('th'):
                # Extract number from prize types like '4th', '5th', '10th'
                try:
                    num = int(prize_type.replace('st', '').replace('nd', '').replace('rd', '').replace('th', ''))
                    return (num + 1, prize_type)  # Add 1 to account for consolation taking position 2
                except ValueError:
                    return (1000, prize_type)
            else:
                return (1000, prize_type)
        
        result.sort(key=prize_sort_key)
        return result

    

# ---------------BAR CODE SCAN SECTION -------------

# Updated Serializer
class TicketCheckSerializer(serializers.Serializer):
    """Enhanced serializer for ticket check request with comprehensive validation"""
    ticket_number = serializers.CharField(
        max_length=50,
        help_text="Ticket number (e.g., W123456)"
    )
    phone_number = serializers.CharField(
        max_length=15,
        help_text="Phone number of the user"
    )
    date = serializers.DateField(
        help_text="Date of the lottery draw (YYYY-MM-DD format)"
    )
    
    def validate_ticket_number(self, value):
        """Validate ticket number format"""
        if not value:
            raise serializers.ValidationError("Ticket number is required")
        
        # Remove any whitespace and convert to uppercase
        value = value.strip().upper()
        
        # Check minimum length (at least 2 characters - 1 for lottery code + 1 for number)
        if len(value) < 2:
            raise serializers.ValidationError("Ticket number must be at least 2 characters long")
        
        # Check that first character is a letter (lottery code)
        if not value[0].isalpha():
            raise serializers.ValidationError("First character must be a letter (lottery code)")
        
        return value
    
    def validate_phone_number(self, value):
        """Validate phone number format and user existence"""
        if not value:
            raise serializers.ValidationError("Phone number is required")
        
        # Remove any whitespace
        value = value.strip()
        
        # Basic phone number format validation
        clean_phone = value.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        if not clean_phone.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits and allowed characters (+, -, spaces, parentheses)")
        
        # Check if user exists with this phone number
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            User.objects.get(phone_number=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this phone number does not exist")
        
        return value
    
    def validate_date(self, value):
        """Validate date is not in the future beyond reasonable limits"""
        if not value:
            raise serializers.ValidationError("Date is required")
        
        from datetime import date, timedelta
        today = date.today()
        
        # Allow checking results up to 1 year in the future (for scheduled draws)
        max_future_date = today + timedelta(days=365)
        
        if value > max_future_date:
            raise serializers.ValidationError("Date cannot be more than 1 year in the future")
        
        # Allow checking results up to 5 years in the past
        min_past_date = today - timedelta(days=1825)  # 5 years
        if value < min_past_date:
            raise serializers.ValidationError("Date cannot be more than 5 years in the past")
        
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        return attrs


        
# <--------NEWS SECTION --------->

class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = ['id', 'headline', 'content', 'image_url', 'news_url', 'source', 'published_at']



#<---------------PREDICTION SECTION ---------------->

# lottery_prediction/serializers.py


class LotteryPredictionRequestSerializer(serializers.Serializer):
    lottery_name = serializers.CharField(max_length=200)
    prize_type = serializers.ChoiceField(choices=[
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
    ])
    
    def validate_lottery_name(self, value):
        """Validate that lottery exists"""
        try:
            lottery = Lottery.objects.get(name__iexact=value)
            return value
        except Lottery.DoesNotExist:
            # Get all available lottery names for better error message
            available_lotteries = list(Lottery.objects.values_list('name', flat=True))
            raise serializers.ValidationError(
                f"Lottery '{value}' does not exist. Available lotteries: {', '.join(available_lotteries)}"
            )

class LotteryPredictionResponseSerializer(serializers.Serializer):
    lottery_name = serializers.CharField()
    prize_type = serializers.CharField()
    predicted_numbers = serializers.ListField(child=serializers.CharField())
    note = serializers.CharField()

#<---------------LIVE SECTION ---------------->

# serializers.py



class LiveVideoSerializer(serializers.ModelSerializer):
    """Serializer for LiveVideo model"""
    
    embed_url = serializers.ReadOnlyField()
    is_live_now = serializers.ReadOnlyField()
    youtube_video_id = serializers.ReadOnlyField()
    
    class Meta:
        model = LiveVideo
        fields = [
            'id',
            'lottery_name',
            'youtube_url',
            'youtube_video_id',
            'embed_url',
            'date',
            'description',
            'status',
            'is_live_now',
            'created_at',
            'updated_at'
        ]