from django.contrib import admin
from django import forms
from django.urls import path, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.utils import timezone
from django.template.response import TemplateResponse
from django.contrib.admin.helpers import AdminForm
from django.utils.html import format_html
from django.shortcuts import render
from django.core.exceptions import PermissionDenied


from .models import LotteryType, LotteryDraw, PrizeCategory, WinningTicket  

class LotteryTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'price', 'first_prize_amount')
    search_fields = ('name', 'code')
    list_filter = ('price',)
    
    # Change button text from "Add" to "New"
    def get_model_perms(self, request):
        perms = super().get_model_perms(request)
        return perms
        
    # Override to change "Add" to "New"
    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'New Lottery'
        return super().add_view(request, form_url, extra_context)
        
    # Custom class attribute to be used in templates
    add_button_label = "New"

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
    list_display = ('full_name', 'draw_date', 'result_declared')
    list_filter = ('lottery_type', 'draw_date', 'result_declared')
    search_fields = ('draw_number', 'lottery_type__name')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('add-result/', self.admin_site.admin_view(self.add_result_view), name='add_lottery_result'),
            path('get-prize-categories/', self.admin_site.admin_view(self.get_prize_categories), name='get_prize_categories'),
        ]
        return custom_urls + urls
    
    def add_result_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
            
        if request.method == 'POST':
            form = DynamicResultEntryForm(request.POST)
            if form.is_valid():
                # Process the form data
                lottery_type = form.cleaned_data['lottery_type']
                draw_number = form.cleaned_data['draw_number']
                draw_date = form.cleaned_data['draw_date']
                result_declared = form.cleaned_data['result_declared']
                
                # Create the LotteryDraw instance
                lottery_draw = LotteryDraw.objects.create(
                    lottery_type=lottery_type,
                    draw_number=draw_number,
                    draw_date=draw_date,
                    result_declared=result_declared
                )
                
                # Process prize data
                prize_categories = PrizeCategory.objects.filter(
                    lottery_type=lottery_type
                ).order_by('amount')
                
                for category in prize_categories:
                    category_name = category.name.lower().replace(' ', '_')
                    
                    # Handle first prize and consolation prizes
                    if "1st" in category.name:
                        first_prize_ticket = form.cleaned_data.get(f'{category_name}_ticket')
                        if first_prize_ticket:
                            # Split into series and number
                            if len(first_prize_ticket) >= 3:
                                series = first_prize_ticket[:2]
                                number = first_prize_ticket[2:]
                                location = form.cleaned_data.get(f'{category_name}_location', '')
                                
                                # Create first prize winning ticket
                                WinningTicket.objects.create(
                                    draw=lottery_draw,
                                    series=series,
                                    number=number,
                                    prize_category=category,
                                    location=location
                                )
                                
                                # Create consolation prizes with same number but different series
                                consolation_category = PrizeCategory.objects.filter(
                                    lottery_type=lottery_type, 
                                    name__icontains='Consolation'
                                ).first()
                                
                                if consolation_category:
                                    consolation_count = form.cleaned_data.get('consolation_count', 0)
                                    
                                    # Get all possible series (common Kerala lottery series)
                                    all_series = ['RA', 'RB', 'RC', 'RD', 'RE', 'RF', 'RG', 'RH', 'RJ', 'RK', 'RL', 'RM']
                                    
                                    # Remove the winning series
                                    if series in all_series:
                                        all_series.remove(series)
                                    
                                    # Create consolation tickets
                                    for i in range(min(consolation_count, len(all_series))):
                                        WinningTicket.objects.create(
                                            draw=lottery_draw,
                                            series=all_series[i],
                                            number=number,
                                            prize_category=consolation_category,
                                            location=""
                                        )
                    
                    # Handle 2nd-5th prizes
                    elif "2nd" in category.name or "3rd" in category.name or "4th" in category.name or "5th" in category.name:
                        tickets_text = form.cleaned_data.get(f'{category_name}_tickets', '')
                        if tickets_text:
                            for line in tickets_text.strip().split('\n'):
                                parts = line.strip().split()
                                if parts:
                                    ticket = parts[0]
                                    if len(ticket) >= 3:
                                        series = ticket[:2]
                                        number = ticket[2:]
                                        location = ' '.join(parts[1:]) if len(parts) > 1 else ''
                                        
                                        WinningTicket.objects.create(
                                            draw=lottery_draw,
                                            series=series,
                                            number=number,
                                            prize_category=category,
                                            location=location
                                        )
                    
                    # Handle 6th-10th prizes (4-digit numbers)
                    else:
                        numbers_text = form.cleaned_data.get(f'{category_name}_numbers', '')
                        if numbers_text:
                            # Split by any whitespace (space, newline, tab)
                            import re
                            numbers = re.split(r'\s+', numbers_text.strip())
                            
                            for number in numbers:
                                if number.strip():
                                    WinningTicket.objects.create(
                                        draw=lottery_draw,
                                        series="",  # No series for lower prize numbers
                                        number=number.strip(),
                                        prize_category=category,
                                        location=""
                                    )
                
                self.message_user(request, f"Successfully added lottery draw {lottery_draw}")
                return HttpResponseRedirect(reverse('admin:index'))
        else:
            form = DynamicResultEntryForm()
        
        context = {
            'title': 'Add Lottery Result',
            'form': form,
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request),
        }
        
        return render(request, 'admin/lottery/lotterydraw/add_result.html', context)
    
    def get_prize_categories(self, request):
        """AJAX view to get prize categories for a lottery type"""
        lottery_type_id = request.GET.get('lottery_type_id')
        
        if lottery_type_id:
            try:
                prize_categories = PrizeCategory.objects.filter(
                    lottery_type_id=lottery_type_id
                ).order_by('amount')
                
                data = [
                    {
                        'id': category.id,
                        'name': category.name,
                        'display_name': category.display_name,
                        'amount': category.amount,
                    }
                    for category in prize_categories
                ]
                
                return JsonResponse({'categories': data})
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)
        
        return JsonResponse({'categories': []})

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
    

class DynamicResultEntryForm(forms.Form):
    lottery_type = forms.ModelChoiceField(
        queryset=LotteryType.objects.all(),
        widget=forms.Select(attrs={'class': 'lottery-type-select'})
    )
    draw_number = forms.IntegerField(min_value=1)
    draw_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.now().date()
    )
    result_declared = forms.BooleanField(required=False, initial=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initially, don't add prize fields until lottery type is selected
        lottery_type_id = self.data.get('lottery_type')
        
        if lottery_type_id:
            try:
                lottery_type = LotteryType.objects.get(id=lottery_type_id)
                prize_categories = PrizeCategory.objects.filter(
                    lottery_type=lottery_type
                ).order_by('amount')
                
                for category in prize_categories:
                    category_name = category.name.lower().replace(' ', '_')
                    
                    # For top prizes (1st to 5th), we need ticket series, number and location
                    if "1st" in category.name or "2nd" in category.name or "3rd" in category.name or "4th" in category.name or "5th" in category.name:
                        # For first prize, we also create consolation prizes
                        if "1st" in category.name:
                            # Add first prize fields
                            self.fields[f'{category_name}_ticket'] = forms.CharField(
                                label=f"{category.name} Ticket Number (with series)",
                                max_length=20,
                                required=True,
                                help_text="Format: XX123456 (series + number)"
                            )
                            self.fields[f'{category_name}_location'] = forms.CharField(
                                label=f"{category.name} Location",
                                max_length=100,
                                required=False
                            )
                            
                            # Add consolation prize fields
                            self.fields[f'consolation_count'] = forms.IntegerField(
                                label="Number of Consolation Prizes",
                                min_value=0,
                                initial=11,  # Most Kerala lotteries have 11 consolation prizes
                                required=False
                            )
                        else:
                            # Add normal fields for 2nd-5th prizes
                            self.fields[f'{category_name}_tickets'] = forms.CharField(
                                label=f"{category.name} Ticket Numbers",
                                widget=forms.Textarea(attrs={'rows': 3}),
                                help_text="One ticket per line. Format: XX123456 LOCATION"
                            )
                    else:
                        # For lower prizes (6th to 10th), we only need 4-digit numbers
                        self.fields[f'{category_name}_numbers'] = forms.CharField(
                            label=f"{category.name} - ₹{category.amount} Numbers",
                            widget=forms.Textarea(attrs={'rows': 5}),
                            help_text="Enter 4-digit numbers, separated by spaces or new lines"
                        )
            except (LotteryType.DoesNotExist, ValueError):
                pass

class LotteryAppAdminSite(admin.AdminSite):
    site_header = 'Lottery Administration'
    site_title = 'Lottery Admin'
    index_title = 'Kerala Lottery Management'
    
    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        # Add custom action buttons to the app list
        for app in app_list:
            if app['app_label'] == 'lottery':  # Replace with your actual app name
                app['custom_actions'] = [
                    {
                        'name': 'Add Lottery Result',
                        'url': reverse('admin:add_lottery_result'),
                        'description': 'Add a new lottery draw result with winners'
                    }
                ]
        return app_list
    
    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['custom_actions'] = [
            {
                'name': 'Add Lottery Result',
                'url': reverse('admin:add_lottery_result'),
                'description': 'Add a new lottery draw result with winners',
                'icon': 'icon-plus'
            }
        ]
        return super().index(request, extra_context)
    

admin_site = LotteryAppAdminSite(name='admin')
# Register your models here.
admin.site.register(LotteryType, LotteryTypeAdmin)
admin.site.register(LotteryDraw, LotteryDrawAdmin)
admin.site.register(PrizeCategory, PrizeCategoryAdmin)
# We keep the WinningTicket model but won't register it with 