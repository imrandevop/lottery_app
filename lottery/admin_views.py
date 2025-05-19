# lottery/admin_views.py
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from .models import PrizeCategory, LotteryDraw

@staff_member_required
def get_prize_categories(request):
    lottery_type_id = request.GET.get('lottery_type_id')
    prize_categories = []
    
    if lottery_type_id:
        prize_categories = list(PrizeCategory.objects.filter(
            lottery_type_id=lottery_type_id
        ).values('id', 'name', 'display_name').order_by('amount'))
    
    return JsonResponse(prize_categories, safe=False)

@staff_member_required
def get_draw_lottery_type(request):
    draw_id = request.GET.get('draw_id')
    result = {'lottery_type_id': None}
    
    if draw_id:
        try:
            draw = LotteryDraw.objects.get(id=draw_id)
            result['lottery_type_id'] = draw.lottery_type_id
        except LotteryDraw.DoesNotExist:
            pass
    
    return JsonResponse(result)