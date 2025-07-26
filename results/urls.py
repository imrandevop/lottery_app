#results\urls.py
from django.urls import path
from .admin_views import add_result_view, edit_result_view
from . import views
from .views import LotteryPredictionAPIView, LiveVideoListView, LotteryWinningPercentageAPI, register_fcm_token, debug_fcm_register, test_send_notification, firebase_status, list_fcm_tokens, test_send_with_details, clear_test_tokens, test_send_direct
app_name = 'results'

urlpatterns = [
    path('admin/add-result/', add_result_view, name='add_result'),
    path('admin/edit-result/<int:result_id>/', edit_result_view, name='edit_result'),

    # List all published lottery results
    path('results/', views.LotteryResultListView.as_view(), name='lottery-results-list'),
    
    # Get today's results
    path('today/', views.today_results, name='today-results'),

    # Get lottery result by unique_id (POST request with unique_id in body)
    path('get-by-unique-id/', views.LotteryResultByUniqueIdView.as_view(), name='lottery-result-by-unique-id'),
    
    path('check-ticket/', views.TicketCheckView.as_view(), name='check-ticket'),

    path('news/', views.NewsListAPIView.as_view(), name='news-list'),

    path('predict/', LotteryPredictionAPIView.as_view(), name='lottery-prediction'),

    path('live-videos/', LiveVideoListView.as_view(), name='live-videos-list'),

    path('lottery-percentage/', LotteryWinningPercentageAPI.as_view(), name='lottery-percentage'),

    # FCM Notification endpoints
    path('fcm/register/', register_fcm_token, name='fcm_register'),
    path('fcm/debug/', debug_fcm_register, name='fcm_debug'),
    path('fcm/test-send/', test_send_notification, name='fcm_test_send'),
    path('debug/firebase/', firebase_status, name='firebase_status'),
    path('fcm/list-tokens/', list_fcm_tokens, name='list_fcm_tokens'),
    path('fcm/test-detailed/', test_send_with_details, name='test_detailed'),
    path('fcm/clear-test-tokens/', clear_test_tokens, name='clear_test_tokens'),
    path('fcm/test-direct/', test_send_direct, name='test_direct'),

    
   
    # Get detailed result by ID
    # path('<int:pk>/', views.LotteryResultDetailView.as_view(), name='lottery-result-detail'),
    
    
    #     # Get all results for specific lottery (with pagination)
    # path('lottery/<str:lottery_code>/results/', views.lottery_results_by_code, name='lottery-results-by-code'),

    #     # Get results for specific date (YYYY-MM-DD)
    # path('date/<str:date_str>/', views.results_by_date, name='results-by-date'),
    
    # # Get latest result for specific lottery
    # path('lottery/<str:lottery_code>/latest/', views.latest_result, name='latest-result'),

]