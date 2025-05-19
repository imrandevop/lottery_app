from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from django import forms
import csv
import io
from django.db.models import Q

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
    fields = ('series', 'number', 'prize_category', 'location')
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if obj:  # If this is not a new object
            formset.form.base_fields['prize_category'].queryset = PrizeCategory.objects.filter(
                lottery_type=obj.lottery_type
            ).order_by('amount')
        return formset
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # This keeps your existing filter logic
        if db_field.name == "prize_category" and hasattr(request, '_obj_') and request._obj_ is not None:
            kwargs["queryset"] = PrizeCategory.objects.filter(
                lottery_type=request._obj_.lottery_type
            ).order_by('amount')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
class LotteryDrawAdminForm(forms.ModelForm):
    class Meta:
        model = LotteryDraw
        fields = '__all__'
    
    class Media:
        js = ('admin/js/lottery_type_filter.js',)


class LotteryDrawAdmin(admin.ModelAdmin):
    form = LotteryDrawAdminForm
    list_display = ('draw_name', 'lottery_type', 'draw_number', 'draw_date', 'result_declared', 'is_new', 'winner_count')
    list_filter = ('lottery_type', 'draw_date', 'result_declared', 'is_new')
    search_fields = ('lottery_type__name', 'lottery_type__code', 'draw_number')
    date_hierarchy = 'draw_date'
    inlines = [WinningTicketInline]
    actions = ['mark_as_declared', 'mark_as_new', 'mark_as_not_new']
    
    def draw_name(self, obj):
        return f"{obj.lottery_type.name} {obj.lottery_type.code} {obj.draw_number}"
    draw_name.short_description = 'Draw Name'
    
    def winner_count(self, obj):
        return obj.winners.count()
    winner_count.short_description = 'Winners'
    
    def mark_as_declared(self, request, queryset):
        queryset.update(result_declared=True)
    mark_as_declared.short_description = "Mark selected draws as result declared"
    
    def mark_as_new(self, request, queryset):
        queryset.update(is_new=True)
    mark_as_new.short_description = "Mark selected draws as NEW"
    
    def mark_as_not_new(self, request, queryset):
        queryset.update(is_new=False)
    mark_as_not_new.short_description = "Remove NEW tag from selected draws"

    def get_form(self, request, obj=None, **kwargs):
    # Store the object for use in formfield_for_foreignkey
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('quick-results/', self.admin_site.admin_view(self.quick_results_view), name='quick-results'),
            path('bulk-upload/', self.admin_site.admin_view(self.bulk_upload_view), name='bulk-upload'),
            path('verify-ticket/', self.admin_site.admin_view(self.verify_ticket_view), name='verify-ticket'),
        ]
        return custom_urls + urls
    
    def quick_results_view(self, request):
        if request.method == 'POST':
            form = QuickResultEntryForm(request.POST)
            if form.is_valid():
                # Get form data
                lottery_type = form.cleaned_data['lottery_type']
                draw_number = form.cleaned_data['draw_number']
                draw_date = form.cleaned_data['draw_date']
                first_prize_series = form.cleaned_data['first_prize_ticket_series']
                first_prize_number = form.cleaned_data['first_prize_ticket_number']
                first_prize_location = form.cleaned_data['first_prize_location']
                
                # Create or update the draw
                draw, created = LotteryDraw.objects.update_or_create(
                    lottery_type=lottery_type,
                    draw_number=draw_number,
                    defaults={
                        'draw_date': draw_date,
                        'result_declared': True,
                        'is_new': True
                    }
                )
                
                # Get first prize category
                first_prize = PrizeCategory.objects.filter(
                    Q(name__icontains='First Prize') | Q(name__icontains='1st Prize'),
                    lottery_type=lottery_type
                ).first()

                if not first_prize:
                    first_prize = PrizeCategory.objects.create(
                        name='First Prize',
                        lottery_type=lottery_type,
                        amount=lottery_type.first_prize_amount,
                        display_name=f'1st Prize Rs {lottery_type.first_prize_amount}/- [{lottery_type.first_prize_amount // 100000} Lakhs]',
                        display_amount=f'Rs {lottery_type.first_prize_amount}/- [{lottery_type.first_prize_amount // 100000} Lakhs]'
                    )
                
                # Create first prize winner
                WinningTicket.objects.update_or_create(
                    draw=draw,
                    prize_category=first_prize,
                    defaults={
                        'series': first_prize_series,
                        'number': first_prize_number,
                        'location': first_prize_location
                    }
                )
                
                messages.success(request, f'Successfully added results for {lottery_type.name} {lottery_type.code} {draw_number}')
                return redirect('admin:lottery_lotterydraw_changelist')
        else:
            form = QuickResultEntryForm()
        
        context = {
            'form': form,
            'title': 'Quick Add Lottery Results',
        }
        return render(request, 'admin/lottery/quick_results.html', context)
    
    def bulk_upload_view(self, request):
        if request.method == 'POST':
            form = BulkResultUploadForm(request.POST, request.FILES)
            if form.is_valid():
                lottery_type = form.cleaned_data['lottery_type']
                draw_number = form.cleaned_data['draw_number']
                draw_date = form.cleaned_data['draw_date']
                
                # Create or update draw
                draw, created = LotteryDraw.objects.update_or_create(
                    lottery_type=lottery_type,
                    draw_number=draw_number,
                    defaults={
                        'draw_date': draw_date,
                        'result_declared': True,
                        'is_new': True
                    }
                )
                
                # Process CSV file
                csv_file = request.FILES['csv_file']
                try:
                    # Read CSV file
                    csv_data = csv_file.read().decode('utf-8')
                    csv_reader = csv.DictReader(io.StringIO(csv_data))
                    
                    # Track success/error counts
                    success_count = 0
                    error_count = 0
                    
                    # Process each row
                    for row in csv_reader:
                        try:
                            prize_name = row.get('prize_name', '').strip()
                            prize_amount = row.get('prize_amount', 0)
                            if prize_amount:
                                prize_amount = int(prize_amount)
                                
                            ticket_series = row.get('series', '').strip()
                            ticket_number = row.get('number', '').strip()
                            location = row.get('location', '').strip()
                            
                            if not prize_name or not ticket_series or not ticket_number:
                                error_count += 1
                                continue
                                
                            # Get or create prize category
                            prize_category, _ = PrizeCategory.objects.get_or_create(
                                name=prize_name,
                                lottery_type=lottery_type,
                                defaults={'amount': prize_amount}
                            )
                            
                            # Create winning ticket
                            WinningTicket.objects.create(
                                draw=draw,
                                prize_category=prize_category,
                                series=ticket_series,
                                number=ticket_number,
                                location=location
                            )
                            
                            success_count += 1
                            
                        except Exception as e:
                            error_count += 1
                    
                    # Show results
                    if success_count > 0:
                        messages.success(request, f'Successfully imported {success_count} winning tickets.')
                    if error_count > 0:
                        messages.warning(request, f'Failed to import {error_count} rows due to errors.')
                        
                    return redirect('admin:lottery_lotterydraw_change', draw.id)
                    
                except Exception as e:
                    messages.error(request, f'Error processing CSV file: {str(e)}')
        else:
            form = BulkResultUploadForm()
            
        context = {
            'form': form,
            'title': 'Bulk Upload Lottery Results',
            'csv_template': 'prize_name,prize_amount,series,number,location\nFirst Prize,7000000,AY,123456,Thrissur\nSecond Prize,500000,BN,234567,\nConsolation Prize,8000,CN,345678,\n',
        }
        return render(request, 'admin/lottery/bulk_upload.html', context)
    
    def verify_ticket_view(self, request):
        result = None
        if request.method == 'POST':
            form = TicketVerificationForm(request.POST)
            if form.is_valid():
                series = form.cleaned_data['ticket_series']
                number = form.cleaned_data['ticket_number']
                
                # Find winning tickets
                winning_tickets = WinningTicket.objects.filter(
                    series__iexact=series,
                    number__iexact=number
                ).select_related('draw', 'draw__lottery_type', 'prize_category')
                
                if winning_tickets.exists():
                    result = {
                        'is_winner': True,
                        'tickets': winning_tickets
                    }
                else:
                    result = {
                        'is_winner': False
                    }
        else:
            form = TicketVerificationForm()
            
        context = {
            'form': form,
            'title': 'Verify Lottery Ticket',
            'result': result
        }
        return render(request, 'admin/lottery/verify_ticket.html', context)

class PrizeCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'amount', 'display_amount', 'lottery_type')
    list_filter = ('lottery_type', 'amount')
    search_fields = ('name', 'display_name')
    autocomplete_fields = ['lottery_type']

class WinningTicketAdminForm(forms.ModelForm):
    class Meta:
        model = WinningTicket
        fields = '__all__'
    
    class Media:
        js = ('admin/js/lottery_ticket_filter.js',)

class WinningTicketAdmin(admin.ModelAdmin):
    form = WinningTicketAdminForm  # Make sure this line is present
    list_display = ('ticket_number', 'draw_info', 'prize_category', 'location')
    list_filter = ('draw__lottery_type', 'prize_category__lottery_type', 'prize_category', 'draw__draw_date')
    search_fields = ('series', 'number', 'location')
    autocomplete_fields = ['draw', 'prize_category']
    
    def ticket_number(self, obj):
        return f"{obj.series} {obj.number}"
    ticket_number.short_description = 'Ticket Number'
    
    def draw_info(self, obj):
        return f"{obj.draw.lottery_type.name} {obj.draw.lottery_type.code} {obj.draw.draw_number} ({obj.draw.draw_date})"
    draw_info.short_description = 'Draw'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # If we're filtering prize categories and we have a draw
        if db_field.name == "prize_category" and request.GET.get('draw__id'):
            draw_id = request.GET.get('draw__id')
            try:
                draw = LotteryDraw.objects.get(id=draw_id)
                kwargs["queryset"] = PrizeCategory.objects.filter(
                    Q(lottery_type=draw.lottery_type) | Q(lottery_type__isnull=True)
                ).order_by('lottery_type', 'amount')
            except LotteryDraw.DoesNotExist:
                pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    # Add this line to use the custom form template
    change_form_template = 'admin/lottery/winningticket/change_form.html'


# Admin site registration
admin.site.register(LotteryType, LotteryTypeAdmin)
admin.site.register(LotteryDraw, LotteryDrawAdmin)
admin.site.register(PrizeCategory, PrizeCategoryAdmin)
admin.site.register(WinningTicket, WinningTicketAdmin)

