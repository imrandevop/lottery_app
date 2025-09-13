# kerala_lottery_project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.views.generic import RedirectView
from django.http import HttpResponse
from .views import HealthCheckView

def loaderio_verification(request):
    return HttpResponse('loaderio-d52bdf3f8ccd2f18052f318fb808f51c', content_type='text/plain')

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

    # Loader.io verification
    path('loaderio-d52bdf3f8ccd2f18052f318fb808f51c.txt', loaderio_verification, name='loaderio_verification'),
]