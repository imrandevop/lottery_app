from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Create an admin user'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        if not User.objects.filter(username='imran').exists():
            User.objects.create_superuser(username='imran', password='imran1210', name='Admin', phone_number='9999999999')
            self.stdout.write(self.style.SUCCESS('Admin user created successfully'))
        else:
            self.stdout.write(self.style.WARNING('Admin user already exists'))
