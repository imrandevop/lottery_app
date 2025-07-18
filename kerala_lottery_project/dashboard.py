from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count
import datetime

class LotteryDashboard:
    @staticmethod
    def get_recent_draws():
        from results.models import LotteryDraw
        return LotteryDraw.objects.filter(
            result_declared=True
        ).order_by('-draw_date')[:5]
    
    @staticmethod
    def get_upcoming_draws():
        from results.models import LotteryDraw
        today = timezone.now().date()
        return LotteryDraw.objects.filter(
            draw_date__gte=today,
            result_declared=False
        ).order_by('draw_date')[:5]
    
    @staticmethod
    def get_lottery_statistics():
        from results.models import LotteryType, LotteryDraw
        stats = []
        for lottery_type in LotteryType.objects.all():
            draw_count = LotteryDraw.objects.filter(
                lottery_type=lottery_type,
                result_declared=True
            ).count()
            stats.append({
                'name': lottery_type.name,
                'code': lottery_type.code,
                'draw_count': draw_count
            })
        return stats