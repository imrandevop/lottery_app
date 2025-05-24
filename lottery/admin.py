# admin.py (path: lottery/admin.py)
from django.contrib import admin
from django import forms
from django.urls import path, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.utils import timezone
from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.template import Context, Template

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

class LotteryResultForm(forms.ModelForm):
    """Custom form for lottery result entry"""
    
    class Meta:
        model = LotteryDraw
        fields = ('lottery_type', 'draw_number', 'draw_date', 'result_declared')
        widgets = {
            'draw_date': forms.DateInput(attrs={'type': 'date'}),
        }

class LotteryDrawAdmin(admin.ModelAdmin):
    form = LotteryResultForm
    list_display = ('full_name', 'draw_date', 'result_declared')
    list_filter = ('lottery_type', 'draw_date', 'result_declared')
    search_fields = ('draw_number', 'lottery_type__name')
    
    # Remove all inlines since we're handling them in the custom view
    inlines = []
    
    fieldsets = (
        ('Lottery Draw Information', {
            'fields': ('lottery_type', 'draw_number', 'draw_date', 'result_declared')
        }),
    )
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('add-result/', self.admin_site.admin_view(self.add_result_view), name='add_lottery_result'),
        ]
        return custom_urls + urls
    
    def add_result_view(self, request):
        """Custom view for adding lottery results with enhanced UI"""
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
                    
                    # Create consolation prizes
                    consolation_amount = float(request.POST.get('consolation_amount', 5000))
                    self._create_consolation_prizes(lottery_draw, first_prize_ticket, consolation_amount)
                
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
                
                # Process Fourth to Tenth Prizes
                prize_models = {
                    'fourth': FourthPrize,
                    'fifth': FifthPrize,
                    'sixth': SixthPrize,
                    'seventh': SeventhPrize,
                    'eighth': EighthPrize,
                    'ninth': NinthPrize,
                    'tenth': TenthPrize
                }
                
                for prize_key, model_class in prize_models.items():
                    self._process_prize_entries(request, lottery_draw, prize_key, model_class)
                
                self.message_user(request, f"Successfully added lottery draw {lottery_draw}")
                return HttpResponseRedirect(reverse('admin:lottery_lotterydraw_change', args=[lottery_draw.pk]))
        else:
            form = LotteryResultForm()
        
        context = {
            'title': 'Add Lottery Result',
            'form': form,
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request),
            'form_url': request.get_full_path(),
            'has_file_field': False,
        }
        
        return render(request, 'admin/lottery/lotterydraw/add_result.html', context)
    
    def _create_consolation_prizes(self, lottery_draw, first_prize_ticket, amount):
        """Create consolation prizes based on first prize ticket"""
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
                    amount=amount
                )
    
    def _process_prize_entries(self, request, lottery_draw, prize_key, model_class):
        """Process both normal and bulk entries for a prize category"""
        
        # Check if bulk entry was used
        bulk_results = request.POST.get(f'{prize_key}_bulk_results', '').strip()
        bulk_amount = request.POST.get(f'{prize_key}_bulk_amount', '')
        
        if bulk_results:
            # Process bulk entry
            amount = float(bulk_amount) if bulk_amount else self._get_default_amount(prize_key)
            
            for line in bulk_results.split('\n'):
                line = line.strip()
                if line:
                    parts = line.split(None, 1)  # Split into ticket and place
                    if parts:
                        ticket = parts[0].strip().upper()
                        place = parts[1].strip().upper() if len(parts) > 1 else ""
                        
                        if ticket:
                            if hasattr(model_class._meta.get_field('ticket_number'), 'max_length'):
                                # For models with ticket_number field (Fourth, Fifth prizes)
                                model_class.objects.create(
                                    draw=lottery_draw,
                                    ticket_number=ticket,
                                    place=place,
                                    amount=amount
                                )
                            else:
                                # For models with number field (Sixth-Tenth prizes)
                                model_class.objects.create(
                                    draw=lottery_draw,
                                    number=ticket,
                                    amount=amount
                                )
        else:
            # Process normal entries
            counter = 0
            while True:
                amount_key = f'{prize_key}_amount_{counter}'
                ticket_key = f'{prize_key}_ticket_{counter}'
                place_key = f'{prize_key}_place_{counter}'
                
                amount = request.POST.get(amount_key, '').strip()
                ticket = request.POST.get(ticket_key, '').strip().upper()
                place = request.POST.get(place_key, '').strip().upper()
                
                if not ticket:
                    break
                
                amount_value = float(amount) if amount else self._get_default_amount(prize_key)
                
                if hasattr(model_class._meta, 'get_field'):
                    try:
                        model_class._meta.get_field('ticket_number')
                        # For models with ticket_number field
                        model_class.objects.create(
                            draw=lottery_draw,
                            ticket_number=ticket,
                            place=place,
                            amount=amount_value
                        )
                    except:
                        # For models with number field
                        model_class.objects.create(
                            draw=lottery_draw,
                            number=ticket,
                            amount=amount_value
                        )
                
                counter += 1
    
    def _get_default_amount(self, prize_key):
        """Get default amount for each prize category"""
        default_amounts = {
            'fourth': 1500000.00,
            'fifth': 100000.00,
            'sixth': 5000.00,
            'seventh': 1000.00,
            'eighth': 500.00,
            'ninth': 100.00,
            'tenth': 50.00
        }
        return default_amounts.get(prize_key, 0.00)

# Simplified admin for individual prize models (only for viewing/editing existing records)
class PrizeAdminBase(admin.ModelAdmin):
    list_display = ('draw', 'amount')
    list_filter = ('draw__lottery_type', 'draw__draw_date')
    search_fields = ('draw__draw_number',)
    readonly_fields = ('draw',)

class FirstPrizeAdmin(PrizeAdminBase):
    list_display = ('draw', 'ticket_number', 'place', 'amount')
    search_fields = ('ticket_number', 'place')

class SecondPrizeAdmin(PrizeAdminBase):
    list_display = ('draw', 'ticket_number', 'place', 'amount')
    search_fields = ('ticket_number', 'place')

class ThirdPrizeAdmin(PrizeAdminBase):
    list_display = ('draw', 'ticket_number', 'place', 'amount')
    search_fields = ('ticket_number', 'place')

class FourthPrizeAdmin(PrizeAdminBase):
    list_display = ('draw', 'ticket_number', 'place', 'amount')
    search_fields = ('ticket_number', 'place')

class FifthPrizeAdmin(PrizeAdminBase):
    list_display = ('draw', 'ticket_number', 'place', 'amount')
    search_fields = ('ticket_number', 'place')

class ConsolationPrizeAdmin(PrizeAdminBase):
    list_display = ('draw', 'ticket_number', 'amount')
    search_fields = ('ticket_number',)

class NumberPrizeAdmin(PrizeAdminBase):
    list_display = ('draw', 'number', 'amount')
    search_fields = ('number',)

# Register models with admin (but hide most from sidebar)
admin.site.register(LotteryType, LotteryTypeAdmin)
admin.site.register(LotteryDraw, LotteryDrawAdmin)

# Register prize models but they won't show in main navigation
admin.site.register(FirstPrize, FirstPrizeAdmin)
admin.site.register(SecondPrize, SecondPrizeAdmin)
admin.site.register(ThirdPrize, ThirdPrizeAdmin)
admin.site.register(FourthPrize, FourthPrizeAdmin)
admin.site.register(FifthPrize, FifthPrizeAdmin)
admin.site.register(ConsolationPrize, ConsolationPrizeAdmin)
admin.site.register(SixthPrize, NumberPrizeAdmin)
admin.site.register(SeventhPrize, NumberPrizeAdmin)
admin.site.register(EighthPrize, NumberPrizeAdmin)
admin.site.register(NinthPrize, NumberPrizeAdmin)
admin.site.register(TenthPrize, NumberPrizeAdmin)