from rest_framework import serializers
from .models import LotteryType, LotteryDraw, PrizeCategory, WinningTicket

class WinningTicketSerializer(serializers.ModelSerializer):
    full_number = serializers.CharField(read_only=True)
    
    class Meta:
        model = WinningTicket
        fields = ['id', 'series', 'number', 'location', 'full_number']

class PrizeCategoryResultSerializer(serializers.ModelSerializer):
    winners = serializers.SerializerMethodField()
    display_name = serializers.CharField(read_only=True)
    display_amount = serializers.CharField(read_only=True)
    
    class Meta:
        model = PrizeCategory
        fields = ['id', 'name', 'display_name', 'amount', 'display_amount', 'winners']
    
    def get_winners(self, obj):
        draw_id = self.context.get('draw_id')
        if draw_id:
            winners = WinningTicket.objects.filter(
                draw_id=draw_id,
                prize_category=obj
            )
            return WinningTicketSerializer(winners, many=True).data
        return []

class LotteryResultSerializer(serializers.ModelSerializer):
    lottery_name = serializers.CharField(source='lottery_type.name')
    lottery_code = serializers.CharField(source='lottery_type.code')
    full_name = serializers.CharField(read_only=True)
    prize_categories = serializers.SerializerMethodField()
    first_prize_winner = serializers.SerializerMethodField()
    
    class Meta:
        model = LotteryDraw
        fields = [
            'id', 'lottery_name', 'lottery_code', 'draw_number', 
            'draw_date', 'full_name', 'is_new', 'prize_categories',
            'first_prize_winner'
        ]
    
    def get_prize_categories(self, obj):
        return PrizeCategoryResultSerializer(
            PrizeCategory.objects.all(),
            context={'draw_id': obj.id},
            many=True
        ).data
    
    def get_first_prize_winner(self, obj):
        first_prize = WinningTicket.objects.filter(
            draw=obj,
            prize_category__name__icontains='First Prize'
        ).first()
        
        if first_prize:
            return {
                'full_number': first_prize.full_number,
                'location': first_prize.location
            }
        return None

class DateGroupedResultsSerializer(serializers.Serializer):
    date = serializers.DateField()
    date_display = serializers.CharField()
    results = LotteryResultSerializer(many=True)