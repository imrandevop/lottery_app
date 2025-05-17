from django.contrib import admin
from django.urls import path, include
from .views import HealthCheckView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('health/', HealthCheckView.as_view(), name='health_check'),
]