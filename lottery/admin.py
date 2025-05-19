from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from django import forms
import csv
import io
from django.db.models import Q
from django.http import JsonResponse

from .models import LotteryType, LotteryDraw, PrizeCategory, WinningTicket

class LotteryTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'price', 'first_prize_amount')
    search_fields = ('name', 'code')
    list_filter = ('price',)

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

class WinningTicketInline(admin.TabularInline):
    model = WinningTicket
    extra = 1
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "prize_category" and hasattr(request, '_obj_') and request._obj_ is not None:
            kwargs["queryset"] = PrizeCategory.objects.filter(
                lottery_type=request._obj_.lottery_type
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
class LotteryDrawAdminForm(forms.ModelForm):
    class Meta:
        model = LotteryDraw
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Start with no choices for prize_category fields in inline forms
        if 'instance' in kwargs and kwargs['instance']:
            # If we're editing an existing object, restrict prize categories
            lottery_type = kwargs['instance'].lottery_type
            if lottery_type:
                # This will affect the PrizeCategory dropdowns in the inline formsets
                # The formset itself will use this queryset as a basis
                prize_field = self.fields.get('first_prize_category', None)
                if prize_field:
                    prize_field.queryset = PrizeCategory.objects.filter(
                        lottery_type=lottery_type
                    ).order_by('amount')
    
    class Media:
        js = ('admin/js/lottery_type_filter.js',)

class LotteryDrawAdmin(admin.ModelAdmin):
    inlines = [WinningTicketInline]
    
    def get_form(self, request, obj=None, **kwargs):
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)

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

    def changelist_view(self, request, extra_context=None):
        """Override to allow filtering by lottery_type in AJAX requests"""
        if 'lottery_type' in request.GET:
            lottery_type_id = request.GET.get('lottery_type')
            categories = list(PrizeCategory.objects.filter(
                lottery_type_id=lottery_type_id
            ).values('id', 'name', 'display_name').order_by('amount'))
            return JsonResponse(categories, safe=False)
        return super().changelist_view(request, extra_context)

class WinningTicketForm(forms.ModelForm):
    class Meta:
        model = WinningTicket
        fields = '__all__'

    class Media:
        js = ('admin/js/winningticket_filter.js',)


class WinningTicketAdmin(admin.ModelAdmin):
    form = WinningTicketForm
    
    def get_form(self, request, obj=None, **kwargs):
        if request.method == 'GET' and 'draw' in request.GET:
            # If a draw ID is provided in GET parameters
            try:
                draw_id = request.GET.get('draw')
                draw = LotteryDraw.objects.get(id=draw_id)
                
                # Create a custom form for this specific request
                class CustomWinningTicketForm(WinningTicketForm):
                    def __init__(self, *args, **kwargs):
                        super().__init__(*args, **kwargs)
                        self.fields['prize_category'].queryset = PrizeCategory.objects.filter(
                            lottery_type=draw.lottery_type
                        )
                
                return CustomWinningTicketForm
            except:
                pass
                
        return super().get_form(request, obj, **kwargs)

# Admin site registration
admin.site.register(LotteryType, LotteryTypeAdmin)
admin.site.register(LotteryDraw, LotteryDrawAdmin)
admin.site.register(PrizeCategory, PrizeCategoryAdmin)
admin.site.register(WinningTicket, WinningTicketAdmin)
