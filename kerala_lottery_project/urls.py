from django.contrib import admin
from django.urls import path, include
from .views import HealthCheckView
from .admin import PrizeCategoryAdmin
from .views import get_lottery_draw

urlpatterns = [
    path('admin/', admin.site.urls),
        # Add this line to directly expose the API endpoint
    path('admin/lottery/prizecategory/by-lottery-type/<int:lottery_type_id>/', 
         admin.site.admin_view(PrizeCategoryAdmin.by_lottery_type_view), 
         name='prizecategory_by_lottery_type'),
    path('admin/api/lottery/lotterydraw/<int:draw_id>/', get_lottery_draw, name='api_get_lottery_draw'),
    
    path('api/users/', include('users.urls')),
    path('api/lottery/', include('lottery.urls')),
    path('health/', HealthCheckView.as_view(), name='health_check'),
]