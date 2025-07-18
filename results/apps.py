# results/apps.py - Update or create this file to register signals

from django.apps import AppConfig

class ResultsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'results'
    
    def ready(self):
        import results.signals  # Import signals when app is ready