#users\urls.py
from django.urls import path
from . import views
from .views import RegisterView, LoginView, user_count_view, LotteryPurchaseView, LotteryStatisticsView, FeedbackView
urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('count/', user_count_view, name='user_count'),
    path('lottery-purchase/', LotteryPurchaseView.as_view(), name='lottery_purchase'),
    path('lottery-statistics/', LotteryStatisticsView.as_view(), name='lottery_statistics'),
    path('feedback/', FeedbackView.as_view(), name='feedback'),
]