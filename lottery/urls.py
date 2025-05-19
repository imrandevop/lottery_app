from django.urls import path
from .views import LotteryResultsView, SingleDrawResultView
from . import admin_views

urlpatterns = [
    # Results URLs
    path('results/', LotteryResultsView.as_view(), name='lottery_results'),
    path('results/<int:draw_id>/', SingleDrawResultView.as_view(), name='single_draw_result'),
    
   
    path('admin/api/prize-categories/', admin_views.get_prize_categories, name='api_prize_categories'),
    path('admin/api/draw-lottery-type/', admin_views.get_draw_lottery_type, name='api_draw_lottery_type'),
]
