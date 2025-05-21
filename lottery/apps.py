# apps.py (path: lottery/apps.py)
from django.apps import AppConfig


class LotteryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lottery'  # This should match your app's directory name
    verbose_name = 'Lotto App'  # This will appear in the admin site
    
    def ready(self):
        """
        Override this method to perform initialization tasks when Django starts.
        """
        # You can import and run any startup code here
        pass