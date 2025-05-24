# admin_site.py (path: lottery/admin_site.py)
from django.contrib.admin import AdminSite
from django.urls import path
from django.shortcuts import redirect

class LotteryAdminSite(AdminSite):
    site_header = "Lottery Administration"
    site_title = "Lottery Admin Portal"
    index_title = "Welcome to Lottery Management System"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            # Add a custom URL that redirects to the lottery result entry
            path('quick-entry/', self.admin_view(self.quick_entry_redirect), name='quick_entry'),
        ]
        return custom_urls + urls
    
    def quick_entry_redirect(self, request):
        """Redirect to the add lottery result page"""
        return redirect('admin:add_lottery_result')
    
    def get_app_list(self, request):
        """
        Return a sorted list showing only Lotteries and Lottery Draws
        """
        app_list = super().get_app_list(request)
        
        # Filter to show only the models we want in sidebar
        for app in app_list:
            if app['app_label'] == 'lottery':
                # Keep only the models we want to show
                filtered_models = []
                
                for model in app['models']:
                    # Only show Lotteries and Lottery Draws in the sidebar
                    if model['object_name'] in ['LotteryType', 'LotteryDraw']:
                        # Customize the display names
                        if model['object_name'] == 'LotteryType':
                            model['name'] = 'Lotteries'
                        elif model['object_name'] == 'LotteryDraw':
                            model['name'] = 'Lottery Draws'
                        
                        filtered_models.append(model)
                
                app['models'] = filtered_models
                
        return app_list
    
    def index(self, request, extra_context=None):
        """
        Custom admin index with lottery-specific dashboard
        """
        extra_context = extra_context or {}
        
        # Add some lottery-specific context
        from .models import LotteryDraw, LotteryType
        from django.utils import timezone
        from datetime import timedelta
        
        # Get recent draws
        recent_draws = LotteryDraw.objects.filter(
            draw_date__gte=timezone.now().date() - timedelta(days=7)
        ).order_by('-draw_date', '-draw_number')[:5]
        
        # Get lottery types
        lottery_types = LotteryType.objects.all()
        
        # Get today's draws
        today_draws = LotteryDraw.objects.filter(
            draw_date=timezone.now().date()
        )
        
        extra_context.update({
            'recent_draws': recent_draws,
            'lottery_types': lottery_types,
            'today_draws': today_draws,
            'total_lottery_types': lottery_types.count(),
            'total_draws_today': today_draws.count(),
        })
        
        return super().index(request, extra_context)

# Create an instance of the custom admin site
lottery_admin_site = LotteryAdminSite(name='lottery_admin')

# Register models with the custom admin site
from .models import LotteryType, LotteryDraw
from .admin import LotteryTypeAdmin, LotteryDrawAdmin

lottery_admin_site.register(LotteryType, LotteryTypeAdmin)
lottery_admin_site.register(LotteryDraw, LotteryDrawAdmin)