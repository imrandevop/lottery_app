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
    fields = ('series', 'number', 'prize_category', 'location')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "prize_category":
            if hasattr(request, '_obj_') and request._obj_ is not None:
                kwargs["queryset"] = PrizeCategory.objects.filter(
                    lottery_type=request._obj_.lottery_type
                ).order_by('amount')
            else:
                # If we don't have a lottery type yet, show no options
                kwargs["queryset"] = PrizeCategory.objects.none()
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
            path('get-prize-categories/', self.admin_site.admin_view(self.get_prize_categories), name='get-prize-categories'),
            path('<path:object_id>/lottery_type/', self.admin_site.admin_view(self.lottery_type_view), name='lotterydraw_lottery_type'),
        ]
        return custom_urls + urls
    
    def get_prize_categories(self, request):
        """API endpoint to get prize categories for a lottery type"""
        lottery_type_id = request.GET.get('lottery_type_id')
        categories = []
        
        if lottery_type_id:
            categories = list(PrizeCategory.objects.filter(
                lottery_type_id=lottery_type_id
            ).values('id', 'name', 'display_name').order_by('amount'))
        
        return JsonResponse(categories, safe=False)
    
    def lottery_type_view(self, request, object_id=None):
        """Return the lottery type ID for a given draw"""
        try:
            draw = self.get_object(request, object_id)
            if draw:
                return JsonResponse({'lottery_type_id': draw.lottery_type_id})
        except:
            pass
        return JsonResponse({'lottery_type_id': None})
    
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

class WinningTicketAdminForm(forms.ModelForm):
    class Meta:
        model = WinningTicket
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If we have an instance or initial data with a draw, filter prize categories
        instance = kwargs.get('instance')
        if instance and instance.draw_id:
            try:
                draw = LotteryDraw.objects.get(id=instance.draw_id)
                self.fields['prize_category'].queryset = PrizeCategory.objects.filter(
                    lottery_type=draw.lottery_type
                ).order_by('amount')
            except LotteryDraw.DoesNotExist:
                pass
        elif 'initial' in kwargs and 'draw' in kwargs['initial']:
            draw_id = kwargs['initial']['draw']
            try:
                draw = LotteryDraw.objects.get(id=draw_id)
                self.fields['prize_category'].queryset = PrizeCategory.objects.filter(
                    lottery_type=draw.lottery_type
                ).order_by('amount')
            except LotteryDraw.DoesNotExist:
                pass
    
    class Media:
        js = ('admin/js/lottery_ticket_filter.js',)

class WinningTicketAdmin(admin.ModelAdmin):
    form = WinningTicketAdminForm
    list_display = ('ticket_number', 'draw_info', 'prize_category', 'location')
    list_filter = ('draw__lottery_type', 'prize_category__lottery_type', 'prize_category', 'draw__draw_date')
    search_fields = ('series', 'number', 'location')
    autocomplete_fields = ['draw']
    
    def ticket_number(self, obj):
        return f"{obj.series} {obj.number}"
    ticket_number.short_description = 'Ticket Number'
    
    def draw_info(self, obj):
        return f"{obj.draw.lottery_type.name} {obj.draw.lottery_type.code} {obj.draw.draw_number} ({obj.draw.draw_date})"
    draw_info.short_description = 'Draw'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # If we're filtering prize categories and we have a draw
        if db_field.name == "prize_category" and request.GET.get('draw'):
            draw_id = request.GET.get('draw')
            try:
                draw = LotteryDraw.objects.get(id=draw_id)
                kwargs["queryset"] = PrizeCategory.objects.filter(
                    lottery_type=draw.lottery_type
                ).order_by('amount')
            except LotteryDraw.DoesNotExist:
                pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    # Add this line to use the custom form template
    change_form_template = 'admin/lottery/winningticket/change_form.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('get-prize-categories-for-draw/', self.admin_site.admin_view(self.get_prize_categories_for_draw), name='get-prize-categories-for-draw'),
        ]
        return custom_urls + urls
    
    def get_prize_categories_for_draw(self, request):
        """API endpoint to get prize categories for a draw"""
        draw_id = request.GET.get('draw_id')
        categories = []
        
        if draw_id:
            try:
                draw = LotteryDraw.objects.get(id=draw_id)
                categories = list(PrizeCategory.objects.filter(
                    lottery_type=draw.lottery_type
                ).values('id', 'name', 'display_name').order_by('amount'))
            except LotteryDraw.DoesNotExist:
                pass
        
        return JsonResponse(categories, safe=False)

# Admin site registration
admin.site.register(LotteryType, LotteryTypeAdmin)
admin.site.register(LotteryDraw, LotteryDrawAdmin)
admin.site.register(PrizeCategory, PrizeCategoryAdmin)
admin.site.register(WinningTicket, WinningTicketAdmin)
