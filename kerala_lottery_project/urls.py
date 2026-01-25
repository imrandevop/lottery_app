# kerala_lottery_project/urls.py

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.generic import RedirectView
from django.http import HttpResponse, JsonResponse
from .views import HealthCheckView
from results.views import register_fcm_token

def loaderio_verification(request):
    return HttpResponse('loaderio-d52bdf3f8ccd2f18052f318fb808f51c', content_type='text/plain')

def api_test_view(request):
    return JsonResponse({"status": "ok", "message": "API endpoint is reachable"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/admin/', permanent=True)),

    # API endpoints
    path('api/results/', include('results.urls')),
    path('api/users/', include('users.urls')),
    
    # 🎯 FLEXIBLE ENDPOINT FOR FLUTTER (Handles with and without trailing slash)
    re_path(r'^api/fcm-token/register/?$', register_fcm_token, name='fcm_token_register_direct'),
    
    # 🧪 TEST ENDPOINT (Tell Flutter dev to try this: /api/fcm-test/)
    path('api/fcm-test/', api_test_view),

    path('health/', HealthCheckView.as_view(), name='health_check'),
    path('loaderio-d52bdf3f8ccd2f18052f318fb808f51c.txt', loaderio_verification, name='loaderio_verification'),
]