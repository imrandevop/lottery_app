from django.core.management.base import BaseCommand
from django.utils import timezone
from results.models import DailyPointsPool
from results.utils import get_india_date

class Command(BaseCommand):
    help = 'Reset daily points pools and cleanup old data'

    def handle(self, *args, **options):
        """
        Run this command daily at midnight India time via cron:
        0 0 * * * /path/to/manage.py reset_daily_pools
        """
        try:
            today = get_india_date()
            
            # Ensure today's pool exists
            pool = DailyPointsPool.get_or_create_today_pool()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully ensured daily pool for {today} '
                    f'with {pool.remaining_points}/{pool.total_daily_budget} points remaining'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error resetting daily pools: {e}')
            )