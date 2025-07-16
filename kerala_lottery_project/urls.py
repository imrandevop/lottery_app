# kerala_lottery_project/urls.py

from django.contrib import admin
from django.urls import path, include
from .views import HealthCheckView
from django.conf import settings
from django.views.generic import RedirectView

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # Redirect root to admin
    path('', RedirectView.as_view(url='/admin/', permanent=True)),
    
    # API endpoints - keeping your existing structure
    path('api/results/', include('results.urls')),
    path('api/users/', include('users.urls')),
    
    # Health check
    path('health/', HealthCheckView.as_view(), name='health_check'),
]