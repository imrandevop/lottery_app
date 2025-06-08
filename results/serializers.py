# serializers.py
from rest_framework import serializers
from .models import Lottery, LotteryResult, PrizeEntry

class PrizeEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrizeEntry
        fields = ['prize_type', 'prize_amount', 'ticket_number', 'place']

class LotteryResultSerializer(serializers.ModelSerializer):
    lottery_name = serializers.CharField(source='lottery.name', read_only=True)
    lottery_code = serializers.CharField(source='lottery.code', read_only=True)
    first_prize = serializers.SerializerMethodField()
    consolation_prizes = serializers.SerializerMethodField()
    
    class Meta:
        model = LotteryResult
        fields = [
            'id', 
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
    prizes = PrizeEntrySerializer(many=True, read_only=True)
    
    class Meta:
        model = LotteryResult
        fields = [
            'id',
            'lottery_name',
            'lottery_code', 
            'date',
            'draw_number',
            'prizes',
            'is_published',
            'created_at',
            'updated_at'    
        ]