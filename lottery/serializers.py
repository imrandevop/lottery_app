# serializers.py (path: lottery/serializers.py)
from rest_framework import serializers
from .models import (
    LotteryType, LotteryDraw,
    FirstPrize, SecondPrize, ThirdPrize, FourthPrize, 
    FifthPrize, ConsolationPrize, SixthPrize, SeventhPrize, 
    EighthPrize, NinthPrize, TenthPrize
)

class LotteryTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LotteryType
        fields = ['id', 'name', 'code', 'price', 'first_prize_amount']

class FirstPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirstPrize
        fields = ['id', 'ticket_number', 'place', 'amount']

class SecondPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecondPrize
        fields = ['id', 'ticket_number', 'place', 'amount']

class ThirdPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThirdPrize
        fields = ['id', 'ticket_number', 'place', 'amount']

class FourthPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FourthPrize
        fields = ['id', 'ticket_number', 'place', 'amount']

class FifthPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FifthPrize
        fields = ['id', 'ticket_number', 'place', 'amount']

class ConsolationPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsolationPrize
        fields = ['id', 'ticket_number', 'amount']

class SixthPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SixthPrize
        fields = ['id', 'number', 'amount']

class SeventhPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeventhPrize
        fields = ['id', 'number', 'amount']

class EighthPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EighthPrize
        fields = ['id', 'number', 'amount']

class NinthPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NinthPrize
        fields = ['id', 'number', 'amount']

class TenthPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenthPrize
        fields = ['id', 'number', 'amount']

class LotteryResultSerializer(serializers.ModelSerializer):
    lottery_type = LotteryTypeSerializer()
    first_prize = FirstPrizeSerializer(read_only=True)
    second_prize = SecondPrizeSerializer(read_only=True)
    third_prize = ThirdPrizeSerializer(read_only=True)
    fourth_prize = FourthPrizeSerializer(read_only=True)
    fifth_prizes = FifthPrizeSerializer(many=True, read_only=True)
    consolation_prizes = ConsolationPrizeSerializer(many=True, read_only=True)
    sixth_prizes = SixthPrizeSerializer(many=True, read_only=True)
    seventh_prizes = SeventhPrizeSerializer(many=True, read_only=True)
    eighth_prizes = EighthPrizeSerializer(many=True, read_only=True)
    ninth_prizes = NinthPrizeSerializer(many=True, read_only=True)
    tenth_prizes = TenthPrizeSerializer(many=True, read_only=True)
    
    class Meta:
        model = LotteryDraw
        fields = [
            'id', 'lottery_type', 'draw_number', 'draw_date', 'result_declared',
            'first_prize', 'second_prize', 'third_prize', 'fourth_prize',
            'fifth_prizes', 'consolation_prizes', 'sixth_prizes', 
            'seventh_prizes', 'eighth_prizes', 'ninth_prizes', 'tenth_prizes'
        ]

class DateGroupedResultsSerializer(serializers.Serializer):
    date = serializers.DateField()
    date_display = serializers.CharField()
    results = LotteryResultSerializer(many=True)