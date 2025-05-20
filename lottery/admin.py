from django.urls import path
from django.shortcuts import render
from django.utils import timezone
from django import forms
from django.http import JsonResponse
from django.contrib import admin  # Import the standard admin module
from .admin_site import lottery_admin_site

from .models import LotteryType, LotteryDraw, PrizeCategory, WinningTicket


class LotteryTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'price', 'first_prize_amount')
    search_fields = ('name', 'code')
    list_filter = ('price',)
    
    # Custom verbose name to change the display in admin UI
    def get_model_perms(self, request):
        perms = super().get_model_perms(request)
        if perms:
            # This changes how it appears in the admin index
            self.model._meta.verbose_name_plural = "Lotteries"
        return perms

class QuickResultEntryForm(forms.Form):
    lottery_type = forms.ModelChoiceField(queryset=LotteryType.objects.all())
    draw_number = forms.IntegerField(min_value=1)
    draw_date = forms.DateField(widget=forms.SelectDateWidget(), initial=timezone.now().date())
    first_prize_ticket_series = forms.CharField(max_length=10)
    first_prize_ticket_number = forms.CharField(max_length=10)
    first_prize_location = forms.CharField(max_length=100, required=False)

class BulkResultUploadForm(forms.Form):
    csv_file = forms.FileField()
    lottery_type = forms.ModelChoiceField(queryset=LotteryType.objects.all())
    draw_number = forms.IntegerField(min_value=1)
    draw_date = forms.DateField(widget=forms.SelectDateWidget(), initial=timezone.now().date())

class TicketVerificationForm(forms.Form):
    ticket_series = forms.CharField(max_length=10)
    ticket_number = forms.CharField(max_length=10)

class LotteryDrawAdminForm(forms.ModelForm):
    class Meta:
        model = LotteryDraw
        fields = '__all__'

class LotteryDrawAdmin(admin.ModelAdmin):
    form = LotteryDrawAdminForm
    list_display = ('full_name', 'draw_date', 'result_declared')
    list_filter = ('lottery_type', 'draw_date', 'result_declared')
    search_fields = ('draw_number', 'lottery_type__name')
    
    # Change display name to "Lottery History"
    def get_model_perms(self, request):
        perms = super().get_model_perms(request)
        if perms:
            # This changes how it appears in the admin index
            self.model._meta.verbose_name_plural = "Lottery History"
        return perms

class PrizeCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'amount', 'display_amount', 'lottery_type')
    list_filter = ('lottery_type', 'amount')
    search_fields = ('name', 'display_name')
    autocomplete_fields = ['lottery_type']
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('by-lottery-type/<int:lottery_type_id>/', self.admin_site.admin_view(self.by_lottery_type_view), name='prizecategory_by_lottery_type'),
        ]
        return custom_urls + urls

    def by_lottery_type_view(self, request, lottery_type_id=None):
        """Return prize categories for a lottery type"""
        if lottery_type_id:
            categories = list(PrizeCategory.objects.filter(
                lottery_type_id=lottery_type_id
            ).values('id', 'name', 'display_name').order_by('amount'))
            return JsonResponse(categories, safe=False)
        return JsonResponse([], safe=False)

# Admin site registration
admin.site.register(LotteryType, LotteryTypeAdmin)
admin.site.register(LotteryDraw, LotteryDrawAdmin)
admin.site.register(PrizeCategory, PrizeCategoryAdmin)
# Removed WinningTicket registration to hide this feature
# Removed WinningTicket registration to hide this feature