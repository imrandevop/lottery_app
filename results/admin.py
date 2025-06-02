# this my admin.py

from django.contrib import admin
from .models import Lottery, LotteryResult, PrizeEntry
from django.contrib.auth.models import Group
from django.forms import ModelForm
from django.forms.widgets import CheckboxInput, Select, DateInput, TextInput
from django.urls import path, reverse
from django.http import HttpResponseRedirect


class LotteryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'price', 'first_price')
    search_fields = ('name', 'code')
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'price', 'first_price', 'description')
        }),
    )


class PrizeEntryInline(admin.TabularInline):
    model = PrizeEntry
    extra = 0
    can_delete = True
    fields = ['prize_type', 'prize_amount', 'ticket_number', 'place']


class LotteryResultForm(ModelForm):
    class Meta:
        model = LotteryResult
        fields = '__all__'
        widgets = {
            'lottery': Select(attrs={'class': 'form-control'}),
            'date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'draw_number': TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter draw number'}),
            'is_published': CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LotteryResultAdmin(admin.ModelAdmin):
    form = LotteryResultForm
    list_display = ['lottery', 'draw_number', 'date', 'is_published', 'created_at']
    list_filter = ['lottery', 'is_published', 'date']
    search_fields = ['draw_number', 'lottery__name']
    inlines = [PrizeEntryInline]
    
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


# Register the admin
admin.site.register(Lottery, LotteryAdmin)
admin.site.register(LotteryResult, LotteryResultAdmin)
admin.site.unregister(Group)