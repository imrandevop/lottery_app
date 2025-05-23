# urls.py - Add these URLs to your existing urls.py file

from django.urls import path
from .views import (
    # Your existing views
    LotteryResultsView, 
    SingleDrawResultView, 
    get_lottery_draw,
    test_json_view,
    
    # New API views for image format
    TodayResultAPIView,
    PreviousDaysResultAPIView,
    CombinedResultsAPIView,
    today_result_simple
)

urlpatterns = [
    # Existing URLs
    path('results/', LotteryResultsView.as_view(), name='lottery_results'),
    path('results/<int:draw_id>/', SingleDrawResultView.as_view(), name='single_draw_result'),
    path('lottery-draw/<int:draw_id>/', get_lottery_draw, name='api_get_lottery_draw'),
    path('test-json/', test_json_view, name='test_json'),
    
    # New API endpoints that match your image format
    path('today-result/', TodayResultAPIView.as_view(), name='today_result_api'),
    path('previous-results/', PreviousDaysResultAPIView.as_view(), name='previous_results_api'),
    path('all-results/', CombinedResultsAPIView.as_view(), name='combined_results_api'),
    path('today-simple/', today_result_simple, name='today_result_simple'),
]