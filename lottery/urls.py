from django.urls import path
from .views import LotteryResultsView, SingleDrawResultView

urlpatterns = [
    # Other URL patterns...
    path('results/', LotteryResultsView.as_view(), name='lottery_results'),
    path('results/<int:draw_id>/', SingleDrawResultView.as_view(), name='single_draw_result'),
]