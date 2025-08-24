from django.core.management.base import BaseCommand
from django.db import connection
from results.models import DailyCashAwarded
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test database connectivity and DailyCashAwarded model access'
    
    def handle(self, *args, **options):
        try:
            # Test basic database connection
            self.stdout.write("Testing database connection...")
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result[0] == 1:
                    self.stdout.write(self.style.SUCCESS("[OK] Database connection: OK"))
                else:
                    self.stdout.write(self.style.ERROR("[ERROR] Database connection: Failed"))
                    return
            
            # Test DailyCashAwarded table access
            self.stdout.write("Testing DailyCashAwarded table access...")
            try:
                count = DailyCashAwarded.objects.count()
                self.stdout.write(self.style.SUCCESS(f"[OK] DailyCashAwarded table: OK ({count} records)"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[ERROR] DailyCashAwarded table error: {e}"))
                return
            
            # Test recent records
            self.stdout.write("Testing recent records access...")
            try:
                recent_records = DailyCashAwarded.objects.order_by('-awarded_at')[:10]
                self.stdout.write(self.style.SUCCESS(f"[OK] Recent records access: OK ({len(list(recent_records))} records)"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[ERROR] Recent records access error: {e}"))
                return
            
            # Test timezone operations
            self.stdout.write("Testing timezone operations...")
            try:
                from django.utils import timezone
                import pytz
                
                ist = pytz.timezone('Asia/Kolkata')
                today_ist = timezone.now().astimezone(ist).date()
                self.stdout.write(self.style.SUCCESS(f"[OK] Timezone operations: OK (Today IST: {today_ist})"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[ERROR] Timezone operations error: {e}"))
                return
            
            self.stdout.write(self.style.SUCCESS("[SUCCESS] All tests passed! Database connectivity is working."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Critical error: {e}"))
            logger.error(f"Database connectivity test failed: {e}")