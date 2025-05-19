from django.urls import path
from .views import LotteryResultsView, SingleDrawResultView
from . import views

urlpatterns = [
    # Other URL patterns...
    path('results/', LotteryResultsView.as_view(), name='lottery_results'),
    path('results/<int:draw_id>/', SingleDrawResultView.as_view(), name='single_draw_result'),
    path('admin/lottery/get-lottery-type/', views.get_lottery_type_for_draw, name='get_lottery_type_for_draw'),
    path('admin/lottery/get-prizes-for-lottery/', views.get_prizes_for_lottery_type, name='get_prizes_for_lottery_type'),

    path('admin/filter-prizes-by-draw/', views.filter_prizes_by_draw, name='filter_prizes_by_draw'),
]