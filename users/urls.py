from django.urls import path
from .views import RegisterView, LoginView, CreateAdminView
urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),

    path('setup-admin/', CreateAdminView.as_view(), name='setup_admin'), 
]