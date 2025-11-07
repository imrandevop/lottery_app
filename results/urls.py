#results\urls.py
from django.urls import path
from .admin_views import (
    add_result_view, edit_result_view, auto_save_ticket,
    start_live_scraping_view, stop_live_scraping_view, get_live_status_view,
    poll_active_sessions_view
)
from . import views
from .views import LotteryPredictionAPIView, LiveVideoListView, LotteryWinningPercentageAPI, register_fcm_token
app_name = 'results'

urlpatterns = [
    path('admin/add-result/', add_result_view, name='add_result'),
    path('admin/edit-result/<int:result_id>/', edit_result_view, name='edit_result'),
    path('admin/auto-save-ticket/', auto_save_ticket, name='auto_save_ticket'),

    # Live scraping endpoints
    path('admin/start-live-scraping/', start_live_scraping_view, name='start_live_scraping'),
    path('admin/stop-live-scraping/', stop_live_scraping_view, name='stop_live_scraping'),
    path('admin/live-status/<int:result_id>/', get_live_status_view, name='get_live_status'),

    # Polling endpoint for external cron service (Cron-Job.org)
    path('poll-sessions/', poll_active_sessions_view, name='poll_sessions'),

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

    path('user-points/', views.UserPointsHistoryView.as_view(), name='user-points'),


    # FCM Notification endpoints
    path('fcm/register/', register_fcm_token, name='fcm_register'),

    
   
    # Get detailed result by ID
    # path('<int:pk>/', views.LotteryResultDetailView.as_view(), name='lottery-result-detail'),
    
    
    #     # Get all results for specific lottery (with pagination)
    # path('lottery/<str:lottery_code>/results/', views.lottery_results_by_code, name='lottery-results-by-code'),

    #     # Get results for specific date (YYYY-MM-DD)
    # path('date/<str:date_str>/', views.results_by_date, name='results-by-date'),
    
    # # Get latest result for specific lottery
    # path('lottery/<str:lottery_code>/latest/', views.latest_result, name='latest-result'),

]