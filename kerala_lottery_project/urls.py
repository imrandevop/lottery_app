from django.contrib import admin
from django.urls import path, include
from .views import HealthCheckView
from django.conf import settings
from django.views.generic import RedirectView

from django.http import HttpResponse
from django.contrib.auth import get_user_model

def create_superuser_view(request):
    User = get_user_model()
    if not User.objects.filter(username="imran").exists():
        User.objects.create_superuser("imran", "imranasvad11@gmail.com", "imran1210")
        return HttpResponse("Superuser created.")
    else:
        return HttpResponse("Superuser already exists.")

urlpatterns = [
    path("create-superuser/", create_superuser_view),
]

urlpatterns = [
      # Add this new URL for the custom admin
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/admin/', permanent=True)),
    path('api/results/', include('results.urls')),  # Add this line
    path('api/users/', include('users.urls')),
    
    path('health/', HealthCheckView.as_view(), name='health_check'),
]

