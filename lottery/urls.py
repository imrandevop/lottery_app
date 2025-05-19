from django.urls import path
from .views import (
    LotteryResultsView, 
    SingleDrawResultView, 
    get_prize_categories_by_lottery_type,
    test_json_view
)
from .admin_views import get_lottery_draw as admin_get_lottery_draw

urlpatterns = [
    # Results URLs
    path('results/', LotteryResultsView.as_view(), name='lottery_results'),
    path('results/<int:draw_id>/', SingleDrawResultView.as_view(), name='single_draw_result'),
    
    # API endpoints
    path('api/prize-categories/<int:lottery_type_id>/', 
         get_prize_categories_by_lottery_type, 
         name='api_get_prize_categories'),
    path('api/lottery-draw/<int:draw_id>/', 
         admin_get_lottery_draw, 
         name='api_get_lottery_draw'),
    path('api/test-json/', 
         test_json_view, 
         name='test_json'),
]
