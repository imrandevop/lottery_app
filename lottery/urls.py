from django.urls import path
from .views import LotteryResultsView, SingleDrawResultView
from .admin_views import get_lottery_draw

urlpatterns = [
    # Results URLs
    path('results/', LotteryResultsView.as_view(), name='lottery_results'),
    path('results/<int:draw_id>/', SingleDrawResultView.as_view(), name='single_draw_result'),
    
   
    path('admin/api/lottery/lotterydraw/<int:draw_id>/', get_lottery_draw, name='api_get_lottery_draw'),
]
