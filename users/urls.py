#users\urls.py
from django.urls import path
from . import views
from .views import RegisterView, LoginView, user_count_view
urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('count/', user_count_view, name='user_count'),
   
]