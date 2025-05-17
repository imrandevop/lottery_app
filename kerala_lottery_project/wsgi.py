import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kerala_lottery_project.settings')

application = get_wsgi_application()