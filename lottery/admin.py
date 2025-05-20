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
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        
        # Store the parent object for use in form initialization
        formset.parent_obj = obj
        
        return formset
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Filter prize_category based on the parent lottery_type
        if db_field.name == "prize_category" and hasattr(request, '_obj_') and request._obj_ is not None:
            kwargs["queryset"] = PrizeCategory.objects.filter(
                lottery_type=request._obj_.lottery_type
            ).order_by('amount')
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
    
    def add_view(self, request, form_url='', extra_context=None):
        """Override the add view to include inline JavaScript"""
        extra_context = extra_context or {}
        extra_context['inline_js'] = self._get_inline_js()
        return super().add_view(request, form_url, extra_context)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Override the change view to include inline JavaScript"""
        extra_context = extra_context or {}
        extra_context['inline_js'] = self._get_inline_js()
        return super().change_view(request, object_id, form_url, extra_context)
    
    def _get_inline_js(self):
        """Return the inline JavaScript for filtering prize categories in inline formsets"""
        return """
        <script type="text/javascript">
        (function($) {
            $(document).ready(function() {
                console.log("Inline LotteryDraw filter script loaded");
                
                // Get the lottery type select
                var lotteryTypeSelect = $('#id_lottery_type');
                
                // Function to update prize categories in all inline forms
                function updateAllPrizeCategories(lotteryTypeId) {
                    console.log("Updating all prize categories for lottery type:", lotteryTypeId);
                    
                    if (!lotteryTypeId) {
                        console.log("No lottery type ID provided");
                        return;
                    }
                    
                    // For each inline form
                    $('.dynamic-winningticket_set').each(function() {
                        var prizeCategorySelect = $(this).find('select[id$="-prize_category"]');
                        
                        // Clear current options
                        prizeCategorySelect.empty();
                        
                        // Add loading option
                        prizeCategorySelect.append('<option value="">Loading...</option>');
                    });
                    
                    // Fetch prize categories for the selected lottery type
                    var apiUrl = '/api/prize-categories/' + lotteryTypeId + '/';
                    console.log('Calling API:', apiUrl);
                    
                    $.ajax({
                        url: apiUrl,
                        type: 'GET',
                        dataType: 'json',
                        success: function(data) {
                            console.log('API response received:', data);
                            
                            // For each inline form
                            $('.dynamic-winningticket_set').each(function() {
                                var prizeCategorySelect = $(this).find('select[id$="-prize_category"]');
                                
                                // Clear current options
                                prizeCategorySelect.empty();
                                
                                // Add empty option
                                prizeCategorySelect.append('<option value="">---------</option>');
                                
                                // Add options for each prize category
                                $.each(data, function(index, category) {
                                    console.log("Adding category:", category.name || category.display_name);
                                    prizeCategorySelect.append(
                                        $('<option></option>').val(category.id).text(category.display_name || category.name)
                                    );
                                });
                            });
                        },
                        error: function(xhr, status, error) {
                            console.error('API error:', status, error);
                            console.log('Response text:', xhr.responseText.substring(0, 500));
                            
                            // For each inline form
                            $('.dynamic-winningticket_set').each(function() {
                                var prizeCategorySelect = $(this).find('select[id$="-prize_category"]');
                                prizeCategorySelect.empty();
                                prizeCategorySelect.append('<option value="">Error loading data</option>');
                            });
                        }
                    });
                }
                
                // Update prize categories when lottery type changes
                lotteryTypeSelect.on('change', function() {
                    var selectedValue = $(this).val();
                    console.log('Lottery type changed to:', selectedValue);
                    updateAllPrizeCategories(selectedValue);
                });
                
                // Initial update if lottery type is already selected
                if (lotteryTypeSelect.length > 0 && lotteryTypeSelect.val()) {
                    console.log("Initial lottery type value:", lotteryTypeSelect.val());
                    updateAllPrizeCategories(lotteryTypeSelect.val());
                }
                
                // When a new inline form is added, update its prize categories
                $(document).on('formset:added', function(event, $row, formsetName) {
                    console.log("Formset added:", formsetName);
                    
                    if (formsetName === 'winningticket_set' && lotteryTypeSelect.val()) {
                        var prizeCategorySelect = $row.find('select[id$="-prize_category"]');
                        
                        // Clear current options
                        prizeCategorySelect.empty();
                        
                        // Add loading option
                        prizeCategorySelect.append('<option value="">Loading...</option>');
                        
                        // Use existing data to populate if available
                        var existingSelects = $('.dynamic-winningticket_set').not($row).find('select[id$="-prize_category"]');
                        if (existingSelects.length > 0) {
                            // Clone options from an existing select
                            var firstSelect = existingSelects.first();
                            firstSelect.find('option').each(function() {
                                prizeCategorySelect.append($(this).clone());
                            });
                        } else {
                            // Fetch from API if no existing selects
                            updateAllPrizeCategories(lotteryTypeSelect.val());
                        }
                    }
                });
            });
        })(django.jQuery);
        </script>
        """



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
    list_display = ('series', 'number', 'prize_category', 'draw')
    def add_view(self, request, form_url='', extra_context=None):
        """Override the add view to include inline JavaScript"""
        extra_context = extra_context or {}
        extra_context['inline_js'] = self._get_inline_js()
        return super().add_view(request, form_url, extra_context)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Override the change view to include inline JavaScript"""
        extra_context = extra_context or {}
        extra_context['inline_js'] = self._get_inline_js()
        return super().change_view(request, object_id, form_url, extra_context)
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Override get_form to dynamically filter prize_category options
        based on the selected lottery_type
        """
        form = super().get_form(request, obj, **kwargs)
        
        # Get the prize_category field from the form
        prize_category_field = form.base_fields['prize_category']
        lottery_type_field = form.base_fields['lottery_type']
        lottery_type_field.help_text = """
            Select a lottery type and click the "Filter Prize Categories" button 
            to show only relevant prize categories.
        """
        
        # CASE 1: When editing an existing object
        if obj and hasattr(obj, 'lottery_type') and obj.lottery_type:
            # Filter prizes by the object's lottery type
            prize_category_field.queryset = PrizeCategory.objects.filter(
                lottery_type=obj.lottery_type
            ).order_by('amount')
            print(f"Filtered categories for existing object's lottery type: {obj.lottery_type}")
        
        # CASE 2: When lottery_type is in GET parameters (from URL)
        elif request.method == 'GET' and 'lottery_type' in request.GET:
            lottery_type_id = request.GET.get('lottery_type')
            try:
                # Try to convert to integer
                lottery_type_id = int(lottery_type_id)
                prize_category_field.queryset = PrizeCategory.objects.filter(
                    lottery_type_id=lottery_type_id
                ).order_by('amount')
                print(f"Filtered categories for lottery type from GET param: {lottery_type_id}")
            except (ValueError, TypeError):
                # If lottery_type_id is not a valid integer
                prize_category_field.queryset = PrizeCategory.objects.none()
                print("Invalid lottery type ID, setting empty queryset")
        
        # CASE 3: Default case
        else:
            # If no lottery type is selected, show no prize categories
            prize_category_field.queryset = PrizeCategory.objects.none()
            print("No lottery type selected, setting empty queryset")
        
        return form
    
    def add_view(self, request, form_url='', extra_context=None):
        """Add custom button to the add form"""
        extra_context = extra_context or {}
        extra_context['show_filter_button'] = True
        return super().add_view(request, form_url, extra_context)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add custom button to the change form"""
        extra_context = extra_context or {}
        extra_context['show_filter_button'] = True
        return super().change_view(request, object_id, form_url, extra_context)
    


# Admin site registration
admin.site.register(LotteryType, LotteryTypeAdmin)
admin.site.register(LotteryDraw, LotteryDrawAdmin)
admin.site.register(PrizeCategory, PrizeCategoryAdmin)
admin.site.register(WinningTicket, WinningTicketAdmin)
