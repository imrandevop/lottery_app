from django.apps import AppConfig

class LotteryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lottery'
    
    def ready(self):
        # Import and register models
        from .admin_site import lottery_admin_site
        from .models import LotteryType, LotteryDraw, PrizeCategory
        from .admin import LotteryTypeAdmin, LotteryDrawAdmin, PrizeCategoryAdmin
        
        # Register models with the admin site
        lottery_admin_site.register(LotteryType, LotteryTypeAdmin)
        lottery_admin_site.register(LotteryDraw, LotteryDrawAdmin)
        lottery_admin_site.register(PrizeCategory, PrizeCategoryAdmin)
        
        # Replace the default admin site if needed
        from django.contrib import admin
        admin.site = lottery_admin_site
