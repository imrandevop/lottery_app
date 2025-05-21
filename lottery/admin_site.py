# from django.contrib import admin
# from django.urls import reverse

# class LotteryAppAdminSite(admin.AdminSite):
#     site_header = 'Lottery Administration'
#     site_title = 'Lottery Admin'
#     index_title = 'Kerala Lottery Management'
    
#     def get_app_list(self, request):
#         app_list = super().get_app_list(request)
#         # Add custom action buttons to the app list
#         for app in app_list:
#             if app['app_label'] == 'lottery':
#                 app['custom_actions'] = [
#                     {
#                         'name': 'Add Lottery Result',
#                         'url': reverse('lottery_admin:add_lottery_result'),
#                         'description': 'Add a new lottery draw result with winners'
#                     }
#                 ]
#         return app_list
    
#     def index(self, request, extra_context=None):
#         extra_context = extra_context or {}
#         extra_context['custom_actions'] = [
#             {
#                 'name': 'Add Lottery Result',
#                 'url': reverse('lottery_admin:add_lottery_result'),
#                 'description': 'Add a new lottery draw result with winners',
#                 'icon': 'icon-plus'
#             }
#         ]
#         return super().index(request, extra_context)

# # Create an instance of the custom admin site
# lottery_admin_site = LotteryAppAdminSite(name='lottery_admin')

from django.contrib.admin import AdminSite

class LotteryAdminSite(AdminSite):
    site_header = "Lottery Administration"
    site_title = "Lottery Admin Portal"
    index_title = "Welcome to Lottery Management System"
    
    def get_app_list(self, request):
        """
        Return a sorted list of all the installed apps that have been
        registered in this site.
        """
        app_list = super().get_app_list(request)
        
        # Custom ordering for the lottery app models
        for app in app_list:
            if app['app_label'] == 'lottery':
                # Define your custom order for models
                desired_order = [
                    'Lotteries',            # Change this to match your actual model name in admin
                    'Lottery Draws',
                    'Consolation prizes',
                    'First prizes',
                    'Second prizes',
                    'Third prizes',
                    'Fourth prizes',
                    'Fifth prizes',
                    'Sixth prizes',
                    'Seventh prizes', 
                    'Eighth prizes',
                    'Ninth prizes',
                    'Tenth prizes',
                    
                    
                ]
                
                # Create a dictionary for quick lookups
                app['models'].sort(
                    key=lambda x: desired_order.index(x['name']) 
                    if x['name'] in desired_order 
                    else len(desired_order)  # Put any unspecified models at the end
                )
                
        return app_list

# Create an instance of the custom admin site
lottery_admin_site = LotteryAdminSite(name='lottery_admin')