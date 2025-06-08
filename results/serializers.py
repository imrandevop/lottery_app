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
            'id',
            'unique_id',  # Added unique_id field
            'lottery_name', 
            'lottery_code',
            'date', 
            'draw_number',
            'first_prize',
            'consolation_prizes',
            'is_published'
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
            'id',
            'unique_id',  # Added unique_id field
            'lottery_name',
            'lottery_code', 
            'date',
            'draw_number',
            'prizes',
            'is_published',
            'created_at',
            'updated_at'    
        ]
    
    def get_prizes(self, obj):
        """Group prizes by prize_type and prize_amount, combining ticket numbers"""
        # Get all prizes for this lottery result
        all_prizes = obj.prizes.all()
        
        if not all_prizes:
            return []
        
        # Group prizes by (prize_type, prize_amount, place)
        grouped_prizes = defaultdict(lambda: {'ticket_numbers': [], 'place': None})
        
        for prize in all_prizes:
            # Create a key based on prize_type, prize_amount, and place
            key = (prize.prize_type, str(prize.prize_amount), prize.place or '')
            grouped_prizes[key]['ticket_numbers'].append(prize.ticket_number)
            grouped_prizes[key]['place'] = prize.place
        
        # Convert grouped data to the desired format
        result = []
        for (prize_type, prize_amount, place), data in grouped_prizes.items():
            # Join all ticket numbers with spaces
            ticket_numbers = ' '.join(data['ticket_numbers'])
            
            prize_data = {
                'prize_type': prize_type,
                'prize_amount': prize_amount,
                'ticket_numbers': ticket_numbers
            }
            
            # Only include place if it's not empty/null
            if place:
                prize_data['place'] = place
            
            result.append(prize_data)
        
        # Sort results by prize type order (1st, 2nd, 3rd, etc., then consolation)
        def prize_sort_key(prize):
            prize_type = prize['prize_type']
            if prize_type == 'consolation':
                return (999, prize_type)  # Put consolation at the end
            elif prize_type.endswith('st') or prize_type.endswith('nd') or prize_type.endswith('rd') or prize_type.endswith('th'):
                # Extract number from prize types like '1st', '2nd', '3rd', '10th'
                try:
                    num = int(prize_type.replace('st', '').replace('nd', '').replace('rd', '').replace('th', ''))
                    return (num, prize_type)
                except ValueError:
                    return (1000, prize_type)
            else:
                return (1000, prize_type)
        
        result.sort(key=prize_sort_key)
        return result