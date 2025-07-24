# Create: results/management/commands/clear_points.py
from django.core.management.base import BaseCommand
from results.models import DailyPoints

class Command(BaseCommand):
    help = 'Clear all daily points records'
    
    def handle(self, *args, **options):
        count = DailyPoints.objects.count()
        self.stdout.write(f"Found {count} DailyPoints records")
        
        if count > 0:
            confirm = input(f"Delete all {count} records? (yes/no): ")
            if confirm.lower() == 'yes':
                DailyPoints.objects.all().delete()
                self.stdout.write("All DailyPoints deleted successfully")
            else:
                self.stdout.write("Operation cancelled")
        else:
            self.stdout.write("No records to delete")