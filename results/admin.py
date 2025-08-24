# admin.py
from django.contrib import admin, messages
from .models import Lottery, LotteryResult, PrizeEntry, ImageUpdate, News, LiveVideo, FcmToken
from .models import DailyPointsPool, UserPointsBalance, PointsTransaction, DailyPointsAwarded
from .models import DailyCashPool, UserCashBalance, CashTransaction, DailyCashAwarded  # Added cash back models
from django.contrib.auth.models import Group
from django.forms import ModelForm, CharField, DecimalField
from django.forms.widgets import CheckboxInput, Select, DateInput, TextInput
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError
import re
from django.utils.html import format_html
from django.shortcuts import render, redirect
from .services.fcm_service import FCMService
from django.db.models import Count

# Custom widget that prevents spaces
class NoSpaceTextInput(TextInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS class and data attributes for JavaScript handling
        self.attrs.update({
            'class': f"{self.attrs.get('class', '')} no-spaces".strip(),
            'data-no-spaces': 'true',
            'oninput': 'this.value = this.value.replace(/\\s/g, "")'
        })

# Custom field that removes spaces from input
class NoSpaceCharField(CharField):
    def clean(self, value):
        if value:
            # Remove all whitespace characters
            value = re.sub(r'\s+', '', str(value))
        return super().clean(value)

class NoSpaceDecimalField(DecimalField):
    def clean(self, value):
        if value:
            # Remove all whitespace characters from decimal input
            value = re.sub(r'\s+', '', str(value))
        return super().clean(value)

class LotteryForm(ModelForm):
    # Only apply no-space restriction to code field
    # name and description will use regular CharField (allows spaces)
    name = CharField()  # Regular CharField - allows spaces
    code = NoSpaceCharField(widget=NoSpaceTextInput())  # No spaces allowed
    description = CharField(widget=TextInput())  # Regular CharField - allows spaces
    
    class Meta:
        model = Lottery
        fields = '__all__'
        
    def clean(self):
        cleaned_data = super().clean()
        # Only remove spaces from code field, leave name and description as is
        if 'code' in cleaned_data and cleaned_data['code']:
            cleaned_data['code'] = re.sub(r'\s+', '', cleaned_data['code'])
        # name and description are left unchanged (spaces allowed)
        return cleaned_data

class LotteryAdmin(admin.ModelAdmin):
    form = LotteryForm
    list_display = ('name', 'code', 'price', 'first_price')
    search_fields = ('name', 'code')
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'price', 'first_price', 'description')
        }),
    )
    
    class Media:
        js = ('results/js/no_spaces_admin.js',)  # We'll create this JS file

class PrizeEntryForm(ModelForm):
    # Override fields to prevent spaces
    ticket_number = NoSpaceCharField(widget=NoSpaceTextInput())
    place = NoSpaceCharField(required=False, widget=NoSpaceTextInput())
    
    class Meta:
        model = PrizeEntry
        fields = '__all__'
        
    def clean(self):
        cleaned_data = super().clean()
        # Remove spaces from ticket number and place
        if 'ticket_number' in cleaned_data and cleaned_data['ticket_number']:
            cleaned_data['ticket_number'] = re.sub(r'\s+', '', cleaned_data['ticket_number'])
        if 'place' in cleaned_data and cleaned_data['place']:
            cleaned_data['place'] = re.sub(r'\s+', '', cleaned_data['place'])
        return cleaned_data

class PrizeEntryInline(admin.TabularInline):
    model = PrizeEntry
    form = PrizeEntryForm
    extra = 0
    can_delete = True
    fields = ['prize_type', 'prize_amount', 'ticket_number', 'place']
    
    class Media:
        js = ('results/js/no_spaces_admin.js',)

class LotteryResultForm(ModelForm):
    # Override draw_number to prevent spaces
    draw_number = NoSpaceCharField(widget=NoSpaceTextInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Enter draw number'
    }))
    
    class Meta:
        model = LotteryResult
        fields = '__all__'
        widgets = {
            'lottery': Select(attrs={'class': 'form-control'}),
            'date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_published': CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_bumper': CheckboxInput(attrs={'class': 'form-check-input'}),
            'results_ready_notification': CheckboxInput(attrs={
                'class': 'form-check-input',
                'title': 'Send push notification to all users'
            }),
        }
        
    def clean(self):
        cleaned_data = super().clean()
        # Remove spaces from draw number
        if 'draw_number' in cleaned_data and cleaned_data['draw_number']:
            cleaned_data['draw_number'] = re.sub(r'\s+', '', cleaned_data['draw_number'])
        return cleaned_data

class LotteryResultAdmin(admin.ModelAdmin):
    form = LotteryResultForm
    list_display = ['lottery', 'draw_number', 'date', 'is_bumper', 'is_published', 
                   'results_ready_notification', 'notification_sent', 'created_at']
    list_filter = ['lottery', 'is_bumper', 'is_published', 'results_ready_notification', 'notification_sent', 'date']
    search_fields = ['draw_number', 'lottery__name']
    inlines = [PrizeEntryInline]
    
    # Add notification field to fieldsets
    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Lottery Information', {
                'fields': ('lottery', 'draw_number', 'date')
            }),
            ('Status & Notifications', {
                'fields': ('is_published', 'is_bumper', 'results_ready_notification'),
                'description': 'Check "Notify users" to send push notification when saving'
            }),
        ]
        if obj:  # Edit mode - show notification status
            fieldsets.append(
                ('Notification Status', {
                    'fields': ('notification_sent',),
                    'classes': ('collapse',)
                }),
            )
            fieldsets.append(
                ('Timestamps', {
                    'fields': ('created_at', 'updated_at'),
                    'classes': ('collapse',)
                }),
            )
        return fieldsets
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Edit mode
            return ['notification_sent', 'created_at', 'updated_at']
        return []
    
    class Media:
        js = ('results/js/no_spaces_admin.js',)
    
    # Keep your existing URL overrides for custom add/edit views
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('add/', self.admin_site.admin_view(self.redirect_to_custom_add), name='results_lotteryresult_add'),
            path('<path:object_id>/change/', self.admin_site.admin_view(self.redirect_to_custom_edit), name='results_lotteryresult_change'),
        ]
        return custom_urls + urls
    
    def redirect_to_custom_add(self, request):
        """Redirect from the standard admin add page to our custom add view."""
        return HttpResponseRedirect('/api/results/admin/add-result/')
    
    def redirect_to_custom_edit(self, request, object_id):
        """Redirect from the standard admin detail page to our custom edit view."""
        result_id = object_id.rstrip('/').split('/')[-1]
        return HttpResponseRedirect(f'/api/results/admin/edit-result/{result_id}/')

# Admin for PrizeEntry with no-space form
class PrizeEntryAdmin(admin.ModelAdmin):
    form = PrizeEntryForm
    list_display = ['lottery_result', 'prize_type', 'ticket_number', 'prize_amount', 'place']
    list_filter = ['prize_type', 'lottery_result__lottery']
    search_fields = ['ticket_number', 'lottery_result__draw_number']
    
    class Media:
        js = ('results/js/no_spaces_admin.js',)

@admin.register(ImageUpdate)
class ImageUpdateAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'updated_at']
    
    # Update the fields to include the new redirect link fields
    fieldsets = (
        ('Image URLs', {
            'fields': ('update_image1', 'update_image2', 'update_image3'),
            'description': 'Add URLs for the three update images'
        }),
        ('Redirect Links', {
            'fields': ('redirect_link1', 'redirect_link2', 'redirect_link3'),
            'description': 'Add redirect URLs for when users tap on each image (optional)'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def has_delete_permission(self, request, obj=None):
        # Allow deletion so users can manage multiple instances
        return True

#<---------------NEWS SECTION---------------->
@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ['headline', 'source', 'published_at', 'is_active', 'created_at']
    list_filter = ['source', 'is_active', 'published_at', 'created_at']
    search_fields = ['headline', 'content', 'source']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'published_at'
    
    fieldsets = (
        ('News Information', {
            'fields': ('headline', 'content', 'source')
        }),
        ('URLs', {
            'fields': ('image_url', 'news_url')
        }),
        ('Publication Details', {
            'fields': ('published_at', 'is_active')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

#<---------------LIVE SECTION---------------->
@admin.register(LiveVideo)
class LiveVideoAdmin(admin.ModelAdmin):
    list_display = [
        'lottery_name',
        'date',
        'status_badge',
        'youtube_link',
        'is_active',
        'created_at'
    ]
    list_filter = [
        'status',
        'is_active',
        'date',
        'created_at'
    ]
    search_fields = [
        'lottery_name',
        'description',
        'youtube_url'
    ]
    readonly_fields = [
        'youtube_video_id',
        'embed_url_display',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'lottery_name',
                'description',
                'date',
                'status',
                'is_active'
            )
        }),
        ('YouTube Information', {
            'fields': (
                'youtube_url',
                'youtube_video_id',
                'embed_url_display'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    # Enable date hierarchy for better navigation
    date_hierarchy = 'date'
    
    # Default ordering
    ordering = ['-date']
    
    # Actions
    actions = ['mark_as_live', 'mark_as_ended', 'mark_as_cancelled']
    
    def status_badge(self, obj):
        """Display status as a colored badge"""
        colors = {
            'scheduled': '#ffc107',  # yellow
            'live': '#28a745',       # green
            'ended': '#6c757d',      # gray
            'cancelled': '#dc3545'   # red
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def youtube_link(self, obj):
        """Display clickable YouTube link"""
        if obj.youtube_url:
            return format_html(
                '<a href="{}" target="_blank" style="color: #dc3545;">🎥 View on YouTube</a>',
                obj.youtube_url
            )
        return '-'
    youtube_link.short_description = 'YouTube'
    
    def embed_url_display(self, obj):
        """Display embed URL for readonly field"""
        if obj.embed_url:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.embed_url,
                obj.embed_url
            )
        return '-'
    embed_url_display.short_description = 'Embed URL'
    
    # Custom actions
    def mark_as_live(self, request, queryset):
        """Mark selected videos as live"""
        count = queryset.update(status='live')
        self.message_user(
            request,
            f'{count} video(s) marked as live.'
        )
    mark_as_live.short_description = 'Mark selected videos as live'
    
    def mark_as_ended(self, request, queryset):
        """Mark selected videos as ended"""
        count = queryset.update(status='ended')
        self.message_user(
            request,
            f'{count} video(s) marked as ended.'
        )
    mark_as_ended.short_description = 'Mark selected videos as ended'
    
    def mark_as_cancelled(self, request, queryset):
        """Mark selected videos as cancelled"""
        count = queryset.update(status='cancelled')
        self.message_user(
            request,
            f'{count} video(s) marked as cancelled.'
        )
    mark_as_cancelled.short_description = 'Mark selected videos as cancelled'
    
    # Custom methods to enhance admin experience
    def get_queryset(self, request):
        """Optimize queryset for admin list view"""
        return super().get_queryset(request).select_related()
    
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        """Customize choice field display"""
        if db_field.name == 'status':
            kwargs['widget'] = Select(
                attrs={'style': 'width: 200px;'}
            )
        return super().formfield_for_choice_field(db_field, request, **kwargs)

#<---------------FCM TOKEN ADMIN---------------->
@admin.register(FcmToken)
class FcmTokenAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number', 'notifications_enabled', 'is_active', 'last_used', 'created_at']
    list_filter = ['notifications_enabled', 'is_active', 'created_at', 'last_used']
    search_fields = ['name', 'phone_number', 'fcm_token']
    readonly_fields = ['fcm_token', 'created_at', 'last_used']
    ordering = ['-last_used']
    
    fieldsets = (
        ('User Information', {
            'fields': ('name', 'phone_number')
        }),
        ('Notification Settings', {
            'fields': ('notifications_enabled', 'is_active')
        }),
        ('Token Information', {
            'fields': ('fcm_token',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_used'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['send_test_notification', 'activate_tokens', 'deactivate_tokens']
    
    def send_test_notification(self, request, queryset):
        """Send test notification to selected users"""
        from .services.fcm_service import FCMService
        
        active_tokens = queryset.filter(is_active=True, notifications_enabled=True)
        if not active_tokens.exists():
            self.message_user(
                request,
                "No active tokens selected for notification.",
                messages.WARNING
            )
            return
        
        # Send test notification
        result = FCMService.send_to_all_users(
            title="Test Notification",
            body="This is a test notification from admin panel.",
            data={'type': 'test', 'source': 'admin'}
        )
        
        self.message_user(
            request,
            f"Test notification sent: {result['success_count']} success, {result['failure_count']} failed",
            messages.SUCCESS if result['success_count'] > 0 else messages.WARNING
        )
    
    send_test_notification.short_description = 'Send test notification'
    
    def activate_tokens(self, request, queryset):
        """Activate selected tokens"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} token(s) activated.', messages.SUCCESS)
    
    activate_tokens.short_description = 'Activate selected tokens'
    
    def deactivate_tokens(self, request, queryset):
        """Deactivate selected tokens"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} token(s) deactivated.', messages.SUCCESS)
    
    deactivate_tokens.short_description = 'Deactivate selected tokens'

#<---------------POINTS SYSTEM SECTION---------------->
@admin.register(DailyPointsPool)
class DailyPointsPoolAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_budget', 'distributed_points', 'remaining_points', 'usage_percentage', 'pool_status']
    list_filter = ['date', 'created_at']
    search_fields = ['date']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-date']
    
    def usage_percentage(self, obj):
        if obj.total_budget > 0:
            percentage = (obj.distributed_points / obj.total_budget) * 100
            color = 'green' if percentage < 70 else 'orange' if percentage < 90 else 'red'
            return format_html(
                '<span style="color: {};">{}</span>',
                color, f"{percentage:.1f}%"
            )
        return "0%"
    usage_percentage.short_description = "Usage %"
    
    def pool_status(self, obj):
        if obj.remaining_points <= 0:
            color = 'red'
            status = 'EMPTY'
        elif obj.remaining_points < 1000:
            color = 'orange'
            status = 'LOW'
        else:
            color = 'green'
            status = 'ACTIVE'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status
        )
    pool_status.short_description = 'Status'
    
    def get_readonly_fields(self, request, obj=None):
        # Make distributed_points and remaining_points readonly if object exists
        if obj:
            return self.readonly_fields + ['distributed_points', 'remaining_points']
        return self.readonly_fields

@admin.register(UserPointsBalance)
class UserPointsBalanceAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'total_points', 'lifetime_earned', 'efficiency_ratio', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['phone_number']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-total_points']
    
    def efficiency_ratio(self, obj):
        """Show current balance vs lifetime earned ratio"""
        if obj.lifetime_earned > 0:
            ratio = (obj.total_points / obj.lifetime_earned) * 100
            return f"{ratio:.1f}%"
        return "N/A"
    efficiency_ratio.short_description = "Balance/Earned %"
    
    def get_readonly_fields(self, request, obj=None):
        # Make points readonly - they should only be changed through transactions
        if obj:
            return self.readonly_fields + ['total_points', 'lifetime_earned']
        return self.readonly_fields

@admin.register(PointsTransaction)
class PointsTransactionAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'transaction_type', 'formatted_points_amount', 'balance_after', 'lottery_name', 'created_at']
    list_filter = ['transaction_type', 'created_at', 'daily_pool_date']
    search_fields = ['phone_number', 'ticket_number', 'lottery_name']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def formatted_points_amount(self, obj):
        if obj.points_amount >= 0:
            return format_html('<span style="color: green;">+{} pts</span>', obj.points_amount)
        else:
            return format_html('<span style="color: red;">{} pts</span>', obj.points_amount)
    formatted_points_amount.short_description = 'Points Amount'
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('phone_number', 'transaction_type', 'points_amount', 'balance_before', 'balance_after')
        }),
        ('Lottery Details', {
            'fields': ('ticket_number', 'lottery_name', 'check_date'),
            'classes': ('collapse',)
        }),
        ('System Info', {
            'fields': ('daily_pool_date', 'description', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        # All fields should be readonly after creation
        if obj:
            return [field.name for field in self.model._meta.fields]
        return self.readonly_fields

@admin.register(DailyPointsAwarded)
class DailyPointsAwardedAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'award_date', 'points_awarded', 'lottery_name', 'ticket_number', 'awarded_at']
    list_filter = ['award_date', 'lottery_name', 'awarded_at']
    search_fields = ['phone_number', 'ticket_number', 'lottery_name']
    readonly_fields = ['awarded_at']
    ordering = ['-award_date', '-awarded_at']
    
    def get_readonly_fields(self, request, obj=None):
        # All fields should be readonly after creation to maintain audit trail
        if obj:
            return [field.name for field in self.model._meta.fields]
        return self.readonly_fields
    
    def has_add_permission(self, request):
        # Prevent manual creation - should only be created through API
        return False
    
    def has_change_permission(self, request, obj=None):
        # Prevent editing - this is an audit table
        return False

#<---------------CASH BACK SYSTEM SECTION---------------->
@admin.register(DailyCashPool)
class DailyCashPoolAdmin(admin.ModelAdmin):
    list_display = ('date', 'formatted_budget', 'formatted_distributed', 'formatted_remaining', 'users_awarded', 'max_users', 'pool_status')
    list_filter = ('date', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-date',)
    
    def formatted_budget(self, obj):
        return f"₹{obj.total_budget}"
    formatted_budget.short_description = 'Total Budget'
    
    def formatted_distributed(self, obj):
        return f"₹{obj.distributed_amount}"
    formatted_distributed.short_description = 'Distributed'
    
    def formatted_remaining(self, obj):
        return f"₹{obj.remaining_amount}"
    formatted_remaining.short_description = 'Remaining'
    
    def pool_status(self, obj):
        if obj.users_awarded >= obj.max_users:
            color = 'red'
            status = 'FULL'
        elif obj.remaining_amount <= 0:
            color = 'red'
            status = 'EMPTY'
        elif obj.users_awarded > 20:
            color = 'orange'
            status = 'HIGH'
        else:
            color = 'green'
            status = 'ACTIVE'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status
        )
    pool_status.short_description = 'Status'
    
    def get_readonly_fields(self, request, obj=None):
        # Make distributed amounts and user count readonly if object exists
        if obj:
            return self.readonly_fields + ['distributed_amount', 'remaining_amount', 'users_awarded']
        return self.readonly_fields

@admin.register(UserCashBalance)
class UserCashBalanceAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'formatted_total_cash', 'formatted_lifetime_earned', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('phone_number',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-total_cash',)
    
    def formatted_total_cash(self, obj):
        return f"₹{obj.total_cash}"
    formatted_total_cash.short_description = 'Total Cash'
    
    def formatted_lifetime_earned(self, obj):
        return f"₹{obj.lifetime_earned_cash}"
    formatted_lifetime_earned.short_description = 'Lifetime Earned'
    
    def get_readonly_fields(self, request, obj=None):
        # Make cash amounts readonly - they should only be changed through transactions
        if obj:
            return self.readonly_fields + ['total_cash', 'lifetime_earned_cash']
        return self.readonly_fields

@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'transaction_type', 'formatted_cash_amount', 'ticket_number', 'lottery_name', 'check_date', 'created_at')
    list_filter = ('transaction_type', 'check_date', 'daily_cash_pool_date', 'created_at')
    search_fields = ('phone_number', 'ticket_number', 'lottery_name')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def formatted_cash_amount(self, obj):
        if obj.cash_amount >= 0:
            return format_html('<span style="color: green;">+₹{}</span>', obj.cash_amount)
        else:
            return format_html('<span style="color: red;">-₹{}</span>', abs(obj.cash_amount))
    formatted_cash_amount.short_description = 'Cash Amount'
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('phone_number', 'transaction_type', 'cash_amount', 'balance_before', 'balance_after')
        }),
        ('Lottery Details', {
            'fields': ('ticket_number', 'lottery_name', 'check_date'),
            'classes': ('collapse',)
        }),
        ('System Info', {
            'fields': ('daily_cash_pool_date', 'description', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        # All fields should be readonly after creation
        if obj:
            return [field.name for field in self.model._meta.fields]
        return self.readonly_fields

@admin.register(DailyCashAwarded)
class DailyCashAwardedAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'formatted_cash_awarded', 'ticket_number', 'lottery_name', 'award_date', 'awarded_at')
    list_filter = ('award_date', 'lottery_name', 'awarded_at')
    search_fields = ('phone_number', 'ticket_number')
    readonly_fields = ('awarded_at',)
    ordering = ('-award_date', '-awarded_at')
    list_per_page = 25  # Reduced from 50 to prevent timeout
    list_max_show_all = 100  # Limit "Show all" functionality
    list_select_related = True  # Optimize database queries
    
    def formatted_cash_awarded(self, obj):
        try:
            return f"₹{obj.cash_awarded}"
        except Exception:
            return "Error"
    formatted_cash_awarded.short_description = 'Cash Awarded'
    
    def get_queryset(self, request):
        """Optimize queryset and handle potential database errors"""
        try:
            # Add timeout protection and optimization
            from django.db import connection
            
            # Set a reasonable timeout for long queries
            with connection.cursor() as cursor:
                cursor.execute("SET statement_timeout = '30s'")
            
            queryset = super().get_queryset(request)
            
            # Apply date filter to recent records only (last 30 days) to improve performance
            from django.utils import timezone
            from datetime import timedelta
            thirty_days_ago = timezone.now().date() - timedelta(days=30)
            queryset = queryset.filter(award_date__gte=thirty_days_ago)
            
            return queryset
            
        except Exception as e:
            messages.error(request, f"Error loading cash awards data: {str(e)}. Please try again or contact support.")
            # Return empty queryset to prevent complete failure
            return self.model.objects.none()
    
    def get_readonly_fields(self, request, obj=None):
        # All fields should be readonly after creation to maintain audit trail
        if obj:
            return [field.name for field in self.model._meta.fields]
        return self.readonly_fields
    
    def has_add_permission(self, request):
        # Prevent manual creation - should only be created through API
        return False
    
    def has_change_permission(self, request, obj=None):
        # Prevent editing - this is an audit table
        return False
    
    def changelist_view(self, request, extra_context=None):
        """Override changelist view to add custom error handling"""
        try:
            return super().changelist_view(request, extra_context)
        except Exception as e:
            messages.error(request, f"Unable to load Daily Cash Awarded data: {str(e)}. This may be due to high server load or database connectivity issues.")
            # Return a simple template or redirect
            from django.shortcuts import render
            return render(request, 'admin/change_list.html', {
                'title': 'Daily Cash Awarded (Error)',
                'app_label': 'results',
                'opts': self.model._meta,
                'has_add_permission': self.has_add_permission(request),
                'error_message': f"Database error: {str(e)}"
            })

# Custom admin actions for points system
def reset_daily_pool(modeladmin, request, queryset):
    """Custom admin action to reset selected daily pools"""
    for pool in queryset:
        pool.distributed_points = 0
        pool.remaining_points = pool.total_budget
        pool.save(update_fields=['distributed_points', 'remaining_points'])
    
    count = queryset.count()
    modeladmin.message_user(request, f"Successfully reset {count} daily pools.")

reset_daily_pool.short_description = "Reset selected pools to full budget"

# Custom admin actions for cash back system
def reset_daily_cash_pool(modeladmin, request, queryset):
    """Custom admin action to reset selected daily cash pools"""
    for pool in queryset:
        pool.distributed_amount = 0.00
        pool.remaining_amount = pool.total_budget
        pool.users_awarded = 0
        pool.save(update_fields=['distributed_amount', 'remaining_amount', 'users_awarded'])
    
    count = queryset.count()
    modeladmin.message_user(request, f"Successfully reset {count} daily cash pools.")

reset_daily_cash_pool.short_description = "Reset selected cash pools to full budget"

# Add the actions to respective admin classes
DailyPointsPoolAdmin.actions = [reset_daily_pool]
DailyCashPoolAdmin.actions = [reset_daily_cash_pool]

# Register the admin
admin.site.register(Lottery, LotteryAdmin)
admin.site.register(LotteryResult, LotteryResultAdmin)
admin.site.register(PrizeEntry, PrizeEntryAdmin)
admin.site.unregister(Group)