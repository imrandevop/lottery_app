from django.http import JsonResponse
from .models import LotteryDraw

def get_lottery_draw(request, draw_id):
    """API endpoint to get lottery draw details"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        draw = LotteryDraw.objects.get(id=draw_id)
        return JsonResponse({
            'id': draw.id,
            'lottery_type': draw.lottery_type_id,
            'draw_number': draw.draw_number,
            'draw_date': draw.draw_date.isoformat(),
        })
    except LotteryDraw.DoesNotExist:
        return JsonResponse({'error': 'Draw not found'}, status=404)