from django.contrib import admin
from django.urls import path, include
from .views import HealthCheckView
from lottery.admin_site import lottery_admin_site

urlpatterns = [
    path('admin/',  lottery_admin_site.urls),  # Add this new URL for the custom admin
    path('api/users/', include('users.urls')),
    path('api/lottery/', include('lottery.urls')),
    path('health/', HealthCheckView.as_view(), name='health_check'),
]