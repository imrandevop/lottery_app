from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _

class LotteryAdminSite(AdminSite):
    # Change the header and title
    site_header = _('Lottery Administration')
    site_title = _('Lottery Admin Portal')
    index_title = _('Lottery Management')
    
    # Completely disable the auth application
    def _build_app_dict(self, request, label=None):
        """
        Build the app dictionary for the admin index page.
        This method is overridden to completely remove 'auth' app.
        """
        app_dict = super()._build_app_dict(request, label)
        
        # Remove the auth app from the app_dict
        if 'auth' in app_dict:
            del app_dict['auth']
            
        return app_dict
        
# Create an instance of the custom admin site
lottery_admin_site = LotteryAdminSite(name='lottery_admin')