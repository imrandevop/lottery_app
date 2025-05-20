from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.utils import timezone
from django import forms
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

class LotteryDrawAdmin(admin.ModelAdmin):
    form = LotteryDrawAdminForm
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

class WinningTicketForm(forms.ModelForm):
    class Meta:
        model = WinningTicket
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add debug printing to help troubleshoot
        print("Initializing WinningTicketForm")
        
        # Add an onchange event to the draw field to submit the form
        self.fields['draw'].widget.attrs.update({'onchange': 'this.form.submit()'})
        
        # Get the form data (POST data)
        data = kwargs.get('data')
        
        # CASE 1: If we have POST data with a draw
        if data and 'draw' in data:
            draw_id = data.get('draw')
            try:
                draw = LotteryDraw.objects.get(id=draw_id)
                lottery_type = draw.lottery_type
                print(f"Selected draw: {draw}, with lottery type: {lottery_type}")
                
                # Get prize categories for this lottery type
                categories = PrizeCategory.objects.filter(lottery_type=lottery_type).order_by('amount')
                print(f"Found {categories.count()} prize categories")
                
                # Set the queryset for prize_category field
                self.fields['prize_category'].queryset = categories
                
            except (ValueError, LotteryDraw.DoesNotExist) as e:
                print(f"Error getting draw: {e}")
                self.fields['prize_category'].queryset = PrizeCategory.objects.none()
        
        # CASE 2: If we have an instance with a draw
        elif self.instance and self.instance.pk and self.instance.draw:
            lottery_type = self.instance.draw.lottery_type
            print(f"Editing existing ticket with draw: {self.instance.draw}, lottery type: {lottery_type}")
            
            # Get prize categories for this lottery type
            categories = PrizeCategory.objects.filter(lottery_type=lottery_type).order_by('amount')
            print(f"Found {categories.count()} prize categories")
            
            self.fields['prize_category'].queryset = categories
        
        # CASE 3: Default case - no draw selected
        else:
            print("No draw selected, setting empty queryset")
            self.fields['prize_category'].queryset = PrizeCategory.objects.none()

class WinningTicketAdmin(admin.ModelAdmin):
    form = WinningTicketForm
    list_display = ('series', 'number', 'prize_category', 'draw')
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return form
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """
        Override changeform_view to handle the draw field change
        """
        # Add debug printing
        print(f"changeform_view called: POST data: {request.method == 'POST'}, object_id: {object_id}")
        
        # If this is a POST request with a draw field but not saving
        if request.method == "POST" and 'draw' in request.POST and '_save' not in request.POST:
            try:
                draw_id = request.POST.get('draw')
                print(f"Processing draw change: draw_id: {draw_id}")
                
                draw = LotteryDraw.objects.get(id=draw_id)
                lottery_type = draw.lottery_type
                print(f"Found draw with lottery type: {lottery_type}")
                
                # Get prize categories for this lottery type
                categories = PrizeCategory.objects.filter(lottery_type=lottery_type).order_by('amount')
                print(f"Found {categories.count()} prize categories: {[c.name for c in categories]}")
                
                # If editing an existing object
                if object_id:
                    obj = self.get_object(request, object_id)
                    form = self.get_form(request, obj)(request.POST, instance=obj)
                else:
                    # Creating a new object
                    form = self.get_form(request)(request.POST)
                
                # Update the prize_category queryset
                form.fields['prize_category'].queryset = categories
                
                # Update the context with the modified form
                extra_context = extra_context or {}
                extra_context.update({
                    'form': form,
                    'prize_categories_filtered': True,
                })
                
            except (ValueError, LotteryDraw.DoesNotExist) as e:
                print(f"Error getting draw: {e}")
        
        return super().changeform_view(request, object_id, form_url, extra_context)
# Admin site registration
admin.site.register(LotteryType, LotteryTypeAdmin)
admin.site.register(LotteryDraw, LotteryDrawAdmin)
admin.site.register(PrizeCategory, PrizeCategoryAdmin)
admin.site.register(WinningTicket, WinningTicketAdmin)