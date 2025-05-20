from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _

class LotteryAdminSite(AdminSite):
    # Change the header and title
    site_header = _('Lottery Administration')
    site_title = _('Lottery Admin Portal')
    index_title = _('Lottery Admin')
    
    # Override get_app_list to customize the sidebar
    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        
        # Filter out the auth app
        app_list = [app for app in app_list if app['app_label'] != 'auth']
        
        # Rename buttons/labels as needed
        for app in app_list:
            if app['app_label'] == 'yourapp':  # Replace with your actual app name
                for model in app['models']:
                    # Customize button labels
                    if model['object_name'] == 'LotteryType':
                        model['name'] = 'Lotteries'
                        model['add_url_name'] = f"{app['app_label']}_{model['object_name'].lower()}_add"
                        model['admin_url_name'] = f"{app['app_label']}_{model['object_name'].lower()}_changelist"
                        
                    elif model['object_name'] == 'LotteryDraw':
                        model['name'] = 'Lottery History'
                        
        return app_list

# Create an instance of the custom admin site
lottery_admin_site = LotteryAdminSite(name='lottery_admin')

# In your admin.py, you'll need to register models with this custom site
# instead of the default admin.site