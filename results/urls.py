from django.urls import path
from .admin_views import add_result_view, edit_result_view

app_name = 'results'

urlpatterns = [
    path('admin/add-result/', add_result_view, name='add_result'),
    path('admin/edit-result/<int:result_id>/', edit_result_view, name='edit_result'),
]