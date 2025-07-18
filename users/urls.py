#users\urls.py
from django.urls import path
from . import views
from .views import RegisterView, LoginView
urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('fcm/register/', views.register_fcm_token, name='register_fcm_token'),
    path('fcm/unregister/', views.unregister_fcm_token, name='unregister_fcm_token'),
    path('notifications/preferences/', views.update_notification_preferences, name='notification_preferences'),

]