# admin.py
from django.contrib import admin, messages
from .models import Lottery, LotteryResult, PrizeEntry, ImageUpdate, News, LiveVideo, FcmToken
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





# Register the admin
admin.site.register(Lottery, LotteryAdmin)
admin.site.register(LotteryResult, LotteryResultAdmin)
admin.site.register(PrizeEntry, PrizeEntryAdmin)
admin.site.unregister(Group)