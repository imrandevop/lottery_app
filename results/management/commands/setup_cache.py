from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Setup database cache table for lottery app'

    def handle(self, *args, **options):
        try:
            call_command('createcachetable', 'lottery_cache_table')
            self.stdout.write(
                self.style.SUCCESS('✅ Database cache table created successfully!')
            )
        except Exception as e:
            if 'already exists' in str(e).lower():
                self.stdout.write(
                    self.style.SUCCESS('✅ Cache table already exists - ready to go!')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️ Cache setup issue: {e}')
                )