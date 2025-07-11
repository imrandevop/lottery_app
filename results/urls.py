from django.urls import path
from .admin_views import add_result_view, edit_result_view
from . import views
from .views import LotteryPredictionAPIView, LiveVideoListView, LotteryWinningPercentageAPI
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



    # Get detailed result by ID
    # path('<int:pk>/', views.LotteryResultDetailView.as_view(), name='lottery-result-detail'),
    
    
    #     # Get all results for specific lottery (with pagination)
    # path('lottery/<str:lottery_code>/results/', views.lottery_results_by_code, name='lottery-results-by-code'),

    #     # Get results for specific date (YYYY-MM-DD)
    # path('date/<str:date_str>/', views.results_by_date, name='results-by-date'),
    
    # # Get latest result for specific lottery
    # path('lottery/<str:lottery_code>/latest/', views.latest_result, name='latest-result'),

]