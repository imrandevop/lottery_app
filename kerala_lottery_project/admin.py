#kerala_lottery_project\admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from .dashboard import LotteryDashboard

# Original admin customization
admin.site.site_title = _("Kerala Lottery Admin")
admin.site.site_header = _("Kerala Lottery Administration")
admin.site.index_title = _("Lottery Management")

# Custom admin index view
admin_index = admin.site.index
def custom_index(request, extra_context=None):
    if extra_context is None:
        extra_context = {}
    extra_context.update({
        'recent_draws': LotteryDashboard.get_recent_draws(),
        'upcoming_draws': LotteryDashboard.get_upcoming_draws(),
        'lottery_statistics': LotteryDashboard.get_lottery_statistics()
    })
    return admin_index(request, extra_context)

admin.site.index = custom_index