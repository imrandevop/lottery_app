from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django import forms
from django.http import JsonResponse
from django.urls import path
from django.utils.html import format_html
from django.utils import timezone
from .models import User, Feedback, UserActivity
from .signals import get_user_count
import pytz

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


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
	list_display = ('phone_number', 'screen_name', 'created_at')
	search_fields = ('phone_number', 'screen_name', 'message')
	list_filter = ('created_at',)


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
	"""
	Custom admin for UserActivity with separate statistics for each app
	Shows: Today's unique users, Usage frequency, New/Existing user status
	"""
	list_display = (
		'short_unique_id',
		'phone_number',
		'app_name',
		'access_count',
		'user_status',
		'first_access_display',
		'last_access_display'
	)
	list_filter = ('app_name', 'first_access', 'last_access')
	search_fields = ('unique_id', 'phone_number')
	readonly_fields = (
		'unique_id',
		'phone_number',
		'app_name',
		'access_count',
		'first_access',
		'last_access',
		'created_at',
		'updated_at',
		'user_status_detail'
	)
	ordering = ('-last_access',)

	fieldsets = (
		('User Identification', {
			'fields': ('unique_id', 'phone_number', 'app_name')
		}),
		('Activity Tracking', {
			'fields': ('access_count', 'first_access', 'last_access', 'user_status_detail')
		}),
		('Metadata', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		}),
	)

	def short_unique_id(self, obj):
		"""Display shortened UUID for better readability"""
		return f"{str(obj.unique_id)[:8]}..."
	short_unique_id.short_description = 'Device ID'

	def first_access_display(self, obj):
		"""Display first access time in IST"""
		ist = pytz.timezone('Asia/Kolkata')
		first_access_ist = obj.first_access.astimezone(ist)
		return first_access_ist.strftime('%Y-%m-%d %H:%M:%S IST')
	first_access_display.short_description = 'First Access'

	def last_access_display(self, obj):
		"""Display last access time in IST"""
		ist = pytz.timezone('Asia/Kolkata')
		last_access_ist = obj.last_access.astimezone(ist)
		return last_access_ist.strftime('%Y-%m-%d %H:%M:%S IST')
	last_access_display.short_description = 'Last Access'

	def user_status(self, obj):
		"""Show if user is new or existing based on phone number join date"""
		if not obj.phone_number:
			return format_html('<span style="color: gray;">No Phone</span>')

		is_new = UserActivity.is_new_user(obj.phone_number)

		if is_new is None:
			return format_html('<span style="color: gray;">No Phone</span>')
		elif is_new:
			return format_html('<span style="color: green; font-weight: bold;">✓ New User</span>')
		else:
			return format_html('<span style="color: blue;">Existing User</span>')
	user_status.short_description = 'User Status'

	def user_status_detail(self, obj):
		"""Detailed user status information for detail view"""
		if not obj.phone_number:
			return "No phone number provided"

		try:
			user = User.objects.get(phone_number=obj.phone_number)
			ist = pytz.timezone('Asia/Kolkata')
			join_date = user.date_joined.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S IST')

			is_new = UserActivity.is_new_user(obj.phone_number)
			status = "New User (Joined Today)" if is_new else "Existing User"

			return f"{status} - Joined: {join_date}"
		except User.DoesNotExist:
			return "Phone number not found in User table (considered new)"
	user_status_detail.short_description = 'User Status Details'

	def changelist_view(self, request, extra_context=None):
		"""Add statistics to the admin changelist view"""
		extra_context = extra_context or {}

		# Get today's stats for each app
		ist = pytz.timezone('Asia/Kolkata')
		today_start = timezone.now().astimezone(ist).replace(hour=0, minute=0, second=0, microsecond=0)

		# Lotto app stats
		lotto_today_users = UserActivity.objects.filter(
			app_name='lotto',
			last_access__gte=today_start
		).count()

		lotto_total_users = UserActivity.objects.filter(app_name='lotto').count()

		# Lotto lite app stats
		lotto_lite_today_users = UserActivity.objects.filter(
			app_name='lotto lite',
			last_access__gte=today_start
		).count()

		lotto_lite_total_users = UserActivity.objects.filter(app_name='lotto lite').count()

		# Add to context
		extra_context['lotto_today_users'] = lotto_today_users
		extra_context['lotto_total_users'] = lotto_total_users
		extra_context['lotto_lite_today_users'] = lotto_lite_today_users
		extra_context['lotto_lite_total_users'] = lotto_lite_total_users
		extra_context['show_activity_stats'] = True

		return super().changelist_view(request, extra_context=extra_context)

	def has_add_permission(self, request):
		"""Disable manual creation of activity records"""
		return False

	def has_delete_permission(self, request, obj=None):
		"""Allow deletion for cleanup purposes"""
		return True
