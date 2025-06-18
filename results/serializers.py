# serializers.py
from rest_framework import serializers
from .models import Lottery, LotteryResult, PrizeEntry
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

class TicketCheckSerializer(serializers.Serializer):
    """Serializer for ticket check request"""
    ticket_number = serializers.CharField(max_length=50)
    phone_number = serializers.CharField(max_length=15)
    date = serializers.DateField()
    
    def validate_phone_number(self, value):
        """Validate that user exists"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            User.objects.get(phone_number=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this phone number does not exist")
        return value