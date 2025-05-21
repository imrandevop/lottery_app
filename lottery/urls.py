# urls.py (path: lottery/urls.py)
from django.urls import path
from .views import (
    LotteryResultsView, 
    SingleDrawResultView, 
    get_lottery_draw,
    test_json_view
)

urlpatterns = [
    # Results URLs
    path('results/', LotteryResultsView.as_view(), name='lottery_results'),
    path('results/<int:draw_id>/', SingleDrawResultView.as_view(), name='single_draw_result'),
    
    # API endpoints
    path('lottery-draw/<int:draw_id>/', 
         get_lottery_draw, 
         name='api_get_lottery_draw'),
    path('test-json/', 
         test_json_view, 
         name='test_json'),
]