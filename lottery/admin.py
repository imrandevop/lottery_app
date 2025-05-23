# admin.py (path: lottery/admin.py)
from django.contrib import admin
from django import forms
from django.urls import path, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.utils import timezone
from django.shortcuts import render
from django.core.exceptions import PermissionDenied

from .models import (
    LotteryType, LotteryDraw, 
    FirstPrize, SecondPrize, ThirdPrize, FourthPrize, 
    FifthPrize, ConsolationPrize, SixthPrize, SeventhPrize, 
    EighthPrize, NinthPrize, TenthPrize
)

class LotteryTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'price', 'first_prize_amount')
    search_fields = ('name', 'code')
    list_filter = ('price',)

    def add_result_view(self, request):
        """Custom view for adding lottery results with a user-friendly interface"""
        if not self.has_add_permission(request):
            raise PermissionDenied
            
        if request.method == 'POST':
            form = LotteryResultForm(request.POST)
            if form.is_valid():
                lottery_draw = form.save()
                
                # Process First Prize
                first_prize_ticket = request.POST.get('firstprize-0-ticket_number', '').strip().upper()
                first_prize_place = request.POST.get('firstprize-0-place', '').strip().upper()
                
                if first_prize_ticket:
                    FirstPrize.objects.create(
                        draw=lottery_draw,
                        ticket_number=first_prize_ticket,
                        place=first_prize_place,
                        amount=10000000.00  # ₹1,00,00,000/-
                    )
                    
                    # Create consolation prizes with the same last 6 digits
                    # but different series (RA, RB, RC, etc.)
                    if len(first_prize_ticket) >= 2:
                        winning_series = first_prize_ticket[:2]
                        winning_number = first_prize_ticket[2:] if len(first_prize_ticket) > 2 else first_prize_ticket
                        
                        # Common series in Kerala lotteries
                        all_series = ['RA', 'RB', 'RC', 'RD', 'RE', 'RF', 'RG', 'RH', 'RJ', 'RK', 'RL', 'RM']
                        
                        # Remove the winning series
                        if winning_series in all_series:
                            all_series.remove(winning_series)
                        
                        # Create consolation prizes
                        for series in all_series:
                            ConsolationPrize.objects.create(
                                draw=lottery_draw,
                                ticket_number=f"{series}{winning_number}",
                                amount=5000.00  # ₹5,000/-
                            )
                
                # Process Second Prize
                second_prize_ticket = request.POST.get('secondprize-0-ticket_number', '').strip().upper()
                second_prize_place = request.POST.get('secondprize-0-place', '').strip().upper()
                
                if second_prize_ticket:
                    SecondPrize.objects.create(
                        draw=lottery_draw,
                        ticket_number=second_prize_ticket,
                        place=second_prize_place,
                        amount=3000000.00  # ₹30,00,000/-
                    )
                
                # Process Third Prize
                third_prize_ticket = request.POST.get('thirdprize-0-ticket_number', '').strip().upper()
                third_prize_place = request.POST.get('thirdprize-0-place', '').strip().upper()
                
                if third_prize_ticket:
                    ThirdPrize.objects.create(
                        draw=lottery_draw,
                        ticket_number=third_prize_ticket,
                        place=third_prize_place,
                        amount=2500000.00  # ₹25,00,000/-
                    )
                
                # Process Fourth Prize
                fourth_prize_ticket = request.POST.get('fourthprize-0-ticket_number', '').strip().upper()
                fourth_prize_place = request.POST.get('fourthprize-0-place', '').strip().upper()
                
                if fourth_prize_ticket:
                    FourthPrize.objects.create(
                        draw=lottery_draw,
                        ticket_number=fourth_prize_ticket,
                        place=fourth_prize_place,
                        amount=1500000.00  # ₹15,00,000/-
                    )
                
                # Process Fifth Prizes
                fifth_prizes_text = request.POST.get('fifth_prizes_bulk', '').strip()
                if fifth_prizes_text:
                    for line in fifth_prizes_text.split('\n'):
                        parts = line.strip().split(None, 1)  # Split into ticket and place
                        if parts:
                            ticket = parts[0].strip().upper()
                            place = parts[1].strip().upper() if len(parts) > 1 else ""
                            
                            if ticket:
                                FifthPrize.objects.create(
                                    draw=lottery_draw,
                                    ticket_number=ticket,
                                    place=place,
                                    amount=100000.00  # ₹1,00,000/-
                                )
                
                # Process bulk entries for 6th-10th prizes
                if form.cleaned_data.get('bulk_sixth_prizes'):
                    self._process_bulk_entries(
                        form.cleaned_data['bulk_sixth_prizes'],
                        SixthPrize,
                        lottery_draw
                    )
                
                if form.cleaned_data.get('bulk_seventh_prizes'):
                    self._process_bulk_entries(
                        form.cleaned_data['bulk_seventh_prizes'],
                        SeventhPrize,
                        lottery_draw
                    )
                
                if form.cleaned_data.get('bulk_eighth_prizes'):
                    self._process_bulk_entries(
                        form.cleaned_data['bulk_eighth_prizes'],
                        EighthPrize,
                        lottery_draw
                    )
                
                if form.cleaned_data.get('bulk_ninth_prizes'):
                    self._process_bulk_entries(
                        form.cleaned_data['bulk_ninth_prizes'],
                        NinthPrize,
                        lottery_draw
                    )
                
                if form.cleaned_data.get('bulk_tenth_prizes'):
                    self._process_bulk_entries(
                        form.cleaned_data['bulk_tenth_prizes'],
                        TenthPrize,
                        lottery_draw
                    )
                
                self.message_user(request, f"Successfully added lottery draw {lottery_draw}")
                return HttpResponseRedirect(reverse('admin:lottery_lotterydraw_change', args=[lottery_draw.pk]))
        else:
            form = LotteryResultForm()
        
        context = {
            'title': 'Add Lottery Result',
            'form': form,
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request),
        }
        
        return render(request, 'admin/lottery/lotterydraw/add_result.html', context)

class FirstPrizeInline(admin.StackedInline):
    model = FirstPrize
    extra = 1
    max_num = 1
    
class SecondPrizeInline(admin.StackedInline):
    model = SecondPrize
    extra = 1
    max_num = 1
    
class ThirdPrizeInline(admin.StackedInline):
    model = ThirdPrize
    extra = 1
    max_num = 1
    
class FourthPrizeInline(admin.StackedInline):
    model = FourthPrize
    extra = 1
    max_num = 1

class FifthPrizeInline(admin.TabularInline):
    model = FifthPrize
    extra = 1
    
    
class ConsolationPrizeInline(admin.TabularInline):
    model = ConsolationPrize
    extra = 1

class SixthPrizeInline(admin.TabularInline):
    model = SixthPrize
    extra = 1
    
class SeventhPrizeInline(admin.TabularInline):
    model = SeventhPrize
    extra = 1
    
class EighthPrizeInline(admin.TabularInline):
    model = EighthPrize
    extra = 1
    
class NinthPrizeInline(admin.TabularInline):
    model = NinthPrize
    extra = 1
    
class TenthPrizeInline(admin.TabularInline):
    model = TenthPrize
    extra = 1

class LotteryResultForm(forms.ModelForm):
    """Custom form for batch entry of prizes"""
    # For bulk entry of 4-digit numbers
    bulk_sixth_prizes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5}), 
        required=False,
        help_text="Enter 6th prize numbers (₹5,000/-), separated by spaces or new lines"
    )
    bulk_seventh_prizes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5}), 
        required=False,
        help_text="Enter 7th prize numbers (₹1,000/-), separated by spaces or new lines"
    )
    bulk_eighth_prizes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5}), 
        required=False,
        help_text="Enter 8th prize numbers (₹500/-), separated by spaces or new lines"
    )
    bulk_ninth_prizes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5}), 
        required=False,
        help_text="Enter 9th prize numbers (₹100/-), separated by spaces or new lines"
    )
    bulk_tenth_prizes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5}), 
        required=False,
        help_text="Enter 10th prize numbers (₹50/-), separated by spaces or new lines"
    )
    
    class Meta:
        model = LotteryDraw
        fields = ('lottery_type', 'draw_number', 'draw_date', 'result_declared')

class LotteryDrawAdmin(admin.ModelAdmin):
    form = LotteryResultForm
    list_display = ('full_name', 'draw_date', 'result_declared')
    list_filter = ('lottery_type', 'draw_date', 'result_declared')
    search_fields = ('draw_number', 'lottery_type__name')
    
    inlines = [
        FirstPrizeInline, ConsolationPrizeInline, SecondPrizeInline, ThirdPrizeInline, FourthPrizeInline,
        FifthPrizeInline,  SixthPrizeInline, SeventhPrizeInline,
        EighthPrizeInline, NinthPrizeInline, TenthPrizeInline
    ]
    
    fieldsets = (
        ('Lottery Draw Information', {
            'fields': ('lottery_type', 'draw_number', 'draw_date', 'result_declared')
        }),
        ('Bulk Entry for Lower Prizes', {
            'fields': (
                'bulk_sixth_prizes', 'bulk_seventh_prizes', 'bulk_eighth_prizes',
                'bulk_ninth_prizes', 'bulk_tenth_prizes'
            ),
            'classes': ('collapse',),
        }),
    )
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('add-result/', self.admin_site.admin_view(self.add_result_view), name='add_lottery_result'),
        ]
        return custom_urls + urls
    
    def add_result_view(self, request):
        """Custom view for adding lottery results with a user-friendly interface"""
        if not self.has_add_permission(request):
            raise PermissionDenied
            
        if request.method == 'POST':
            form = LotteryResultForm(request.POST)
            if form.is_valid():
                lottery_draw = form.save()
                
                # Process bulk entries for prize numbers
                if form.cleaned_data.get('bulk_sixth_prizes'):
                    self._process_bulk_entries(
                        form.cleaned_data['bulk_sixth_prizes'],
                        SixthPrize,
                        lottery_draw
                    )
                
                if form.cleaned_data.get('bulk_seventh_prizes'):
                    self._process_bulk_entries(
                        form.cleaned_data['bulk_seventh_prizes'],
                        SeventhPrize,
                        lottery_draw
                    )
                
                if form.cleaned_data.get('bulk_eighth_prizes'):
                    self._process_bulk_entries(
                        form.cleaned_data['bulk_eighth_prizes'],
                        EighthPrize,
                        lottery_draw
                    )
                
                if form.cleaned_data.get('bulk_ninth_prizes'):
                    self._process_bulk_entries(
                        form.cleaned_data['bulk_ninth_prizes'],
                        NinthPrize,
                        lottery_draw
                    )
                
                if form.cleaned_data.get('bulk_tenth_prizes'):
                    self._process_bulk_entries(
                        form.cleaned_data['bulk_tenth_prizes'],
                        TenthPrize,
                        lottery_draw
                    )
                
                self.message_user(request, f"Successfully added lottery draw {lottery_draw}")
                return HttpResponseRedirect(reverse('admin:lottery_lotterydraw_change', args=[lottery_draw.pk]))
        else:
            form = LotteryResultForm()
        
        context = {
            'title': 'Add Lottery Result',
            'form': form,
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request),
        }
        
        return render(request, 'admin/lottery/lotterydraw/add_result.html', context)
    
    def _process_bulk_entries(self, bulk_text, model_class, lottery_draw):
        """Helper method to process bulk entries for prize numbers"""
        # Split by whitespace (spaces, tabs, newlines)
        import re
        numbers = re.split(r'\s+', bulk_text.strip())
        
        for number in numbers:
            if number.strip():
                model_class.objects.create(
                    draw=lottery_draw,
                    number=number.strip()
                )
    
    def save_model(self, request, obj, form, change):
        """Handle bulk entries when saving via the normal admin form"""
        super().save_model(request, obj, form, change)
        
        # Process bulk entries
        if form.cleaned_data.get('bulk_sixth_prizes'):
            self._process_bulk_entries(
                form.cleaned_data['bulk_sixth_prizes'],
                SixthPrize,
                obj
            )
        
        if form.cleaned_data.get('bulk_seventh_prizes'):
            self._process_bulk_entries(
                form.cleaned_data['bulk_seventh_prizes'],
                SeventhPrize,
                obj
            )
        
        if form.cleaned_data.get('bulk_eighth_prizes'):
            self._process_bulk_entries(
                form.cleaned_data['bulk_eighth_prizes'],
                EighthPrize,
                obj
            )
        
        if form.cleaned_data.get('bulk_ninth_prizes'):
            self._process_bulk_entries(
                form.cleaned_data['bulk_ninth_prizes'],
                NinthPrize,
                obj
            )
        
        if form.cleaned_data.get('bulk_tenth_prizes'):
            self._process_bulk_entries(
                form.cleaned_data['bulk_tenth_prizes'],
                TenthPrize,
                obj
            )

# Register all models with admin
admin.site.register(LotteryType, LotteryTypeAdmin)
admin.site.register(LotteryDraw, LotteryDrawAdmin)
admin.site.register(FirstPrize)
admin.site.register(SecondPrize)
admin.site.register(ThirdPrize)
admin.site.register(FourthPrize)
admin.site.register(FifthPrize)
admin.site.register(ConsolationPrize)
admin.site.register(SixthPrize)
admin.site.register(SeventhPrize)
admin.site.register(EighthPrize)
admin.site.register(NinthPrize)
admin.site.register(TenthPrize)

# If you're using a custom admin site as in your existing code
from .admin_site import lottery_admin_site

lottery_admin_site.register(LotteryType, LotteryTypeAdmin)
lottery_admin_site.register(LotteryDraw, LotteryDrawAdmin)
lottery_admin_site.register(FirstPrize)
lottery_admin_site.register(SecondPrize)
lottery_admin_site.register(ThirdPrize)
lottery_admin_site.register(FourthPrize)
lottery_admin_site.register(FifthPrize)
lottery_admin_site.register(ConsolationPrize)
lottery_admin_site.register(SixthPrize)
lottery_admin_site.register(SeventhPrize)
lottery_admin_site.register(EighthPrize)
lottery_admin_site.register(NinthPrize)
lottery_admin_site.register(TenthPrize)