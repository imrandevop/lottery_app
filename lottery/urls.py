from django.urls import path
from .views import LotteryResultsView, SingleDrawResultView
from . import views

urlpatterns = [
    # Results URLs
    path('results/', LotteryResultsView.as_view(), name='lottery_results'),
    path('results/<int:draw_id>/', SingleDrawResultView.as_view(), name='single_draw_result'),
    
   
    path('admin/get_prices/<int:lottery_id>/', views.get_prices_for_lottery),
]
