from django.urls import path
from .views import LotteryResultsView, SingleDrawResultView
from . import views

urlpatterns = [
    # Results URLs
    path('results/', LotteryResultsView.as_view(), name='lottery_results'),
    path('results/<int:draw_id>/', SingleDrawResultView.as_view(), name='single_draw_result'),
    
    # Admin AJAX URLs - Update these to match exactly what's in your JavaScript
    path('/admin/lottery/get-lottery-type/', views.get_lottery_type_for_draw, name='get_lottery_type_for_draw'),
    path('/admin/lottery/get-prizes-for-lottery/', views.get_prizes_for_lottery_type, name='get_prizes_for_lottery_type'),
]
