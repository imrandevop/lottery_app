from django.contrib import admin
from django.urls import path, include
from .views import HealthCheckView
from django.conf import settings
from django.views.generic import RedirectView



urlpatterns = [
      # Add this new URL for the custom admin
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/admin/', permanent=True)),
    path('api/results/', include('results.urls')),  # Add this line
    path('api/users/', include('users.urls')),
    
    path('health/', HealthCheckView.as_view(), name='health_check'),
]

