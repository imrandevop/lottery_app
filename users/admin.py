from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django import forms
from django.http import JsonResponse
from django.urls import path
from django.utils.html import format_html
from .models import User
from .signals import get_user_count

class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('phone_number', 'name')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ('phone_number', 'name', 'password', 'is_active', 'is_staff')

    def clean_password(self):
        return self.initial["password"]

class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_list_template = 'admin/users/user/change_list.html'

    list_display = ('phone_number', 'name', 'date_joined', 'is_staff')
    list_filter = ('is_staff', 'is_active', 'date_joined')
    fieldsets = (
        (None, {'fields': ('phone_number', 'name', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('date_joined',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'name', 'password1', 'password2'),
        }),
    )
    search_fields = ('phone_number', 'name')
    ordering = ('-date_joined',)
    filter_horizontal = ('groups', 'user_permissions',)
    readonly_fields = ('date_joined',)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('user-count/', self.admin_site.admin_view(self.user_count_view), name='users_user_count'),
        ]
        return custom_urls + urls
    
    def user_count_view(self, request):
        """Admin view to get current user count for AJAX requests"""
        count = get_user_count()
        return JsonResponse({'count': count})
    
    def save_model(self, request, obj, form, change):
        """Override save_model to trigger counter updates"""
        super().save_model(request, obj, form, change)
        # The signal will handle the counter update automatically
    
    def delete_model(self, request, obj):
        """Override delete_model to trigger counter updates"""
        super().delete_model(request, obj)
        # The signal will handle the counter update automatically
        
    def changelist_view(self, request, extra_context=None):
        """Override changelist_view to add user count to context"""
        extra_context = extra_context or {}
        extra_context['user_count'] = get_user_count()
        extra_context['show_user_counter'] = True
        return super().changelist_view(request, extra_context=extra_context)

admin.site.register(User, UserAdmin)

