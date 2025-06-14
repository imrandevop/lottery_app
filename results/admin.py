from django.contrib import admin
from .models import Lottery, LotteryResult, PrizeEntry
from django.contrib.auth.models import Group
from django.forms import ModelForm, CharField, DecimalField
from django.forms.widgets import CheckboxInput, Select, DateInput, TextInput
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError
import re


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
    # Override fields to use no-space versions
    name = NoSpaceCharField(widget=NoSpaceTextInput())
    code = NoSpaceCharField(widget=NoSpaceTextInput())
    description = NoSpaceCharField(widget=NoSpaceTextInput())
    
    class Meta:
        model = Lottery
        fields = '__all__'
        
    def clean(self):
        cleaned_data = super().clean()
        # Additional cleaning for all text fields
        for field_name, value in cleaned_data.items():
            if isinstance(value, str):
                cleaned_data[field_name] = re.sub(r'\s+', '', value)
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
        }
        
    def clean(self):
        cleaned_data = super().clean()
        # Remove spaces from draw number
        if 'draw_number' in cleaned_data and cleaned_data['draw_number']:
            cleaned_data['draw_number'] = re.sub(r'\s+', '', cleaned_data['draw_number'])
        return cleaned_data


class LotteryResultAdmin(admin.ModelAdmin):
    form = LotteryResultForm
    list_display = ['lottery', 'draw_number', 'date','is_bumper', 'is_published', 'created_at']
    list_filter = ['lottery','is_bumper', 'is_published', 'date']
    search_fields = ['draw_number', 'lottery__name']
    inlines = [PrizeEntryInline]
    
    class Media:
        js = ('results/js/no_spaces_admin.js',)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('add/', self.admin_site.admin_view(self.redirect_to_custom_add), name='results_lotteryresult_add'),
            # Add a new URL pattern to catch detail view requests and redirect to edit
            path('<path:object_id>/', self.admin_site.admin_view(self.redirect_to_custom_edit), name='results_lotteryresult_change'),
        ]
        return custom_urls + urls
    
    def redirect_to_custom_add(self, request):
        """Redirect from the standard admin add page to our custom add view."""
        return HttpResponseRedirect(reverse('results:add_result'))
    
    def redirect_to_custom_edit(self, request, object_id):
        """Redirect from the standard admin detail page to our custom edit view."""
        # Extract just the numeric ID from the object_id path
        result_id = object_id.split('/')[0]
        return HttpResponseRedirect(reverse('results:edit_result', kwargs={'result_id': result_id}))


# Admin for PrizeEntry with no-space form
class PrizeEntryAdmin(admin.ModelAdmin):
    form = PrizeEntryForm
    list_display = ['lottery_result', 'prize_type', 'ticket_number', 'prize_amount', 'place']
    list_filter = ['prize_type', 'lottery_result__lottery']
    search_fields = ['ticket_number', 'lottery_result__draw_number']
    
    class Media:
        js = ('results/js/no_spaces_admin.js',)


# Register the admin
admin.site.register(Lottery, LotteryAdmin)
admin.site.register(LotteryResult, LotteryResultAdmin)
admin.site.register(PrizeEntry, PrizeEntryAdmin)
admin.site.unregister(Group)